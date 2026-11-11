"""The Kavach agent (ARCH §9.3), built on LangGraph.

Conversation graph, one run per customer message, memory checkpointed per conversation:
    ingest → guard → understand → plan_read → act → respond
Approval graph, one thread per escalation, pauses with `interrupt()` until the seller decides,
survives restarts (Postgres checkpointer), then executes and tells the customer:
    await_seller ⏸ → finish

The agent can READ (store, reader key) and PROPOSE. It cannot write: every change goes through the trust
service, which re-checks the facts and alone holds the signing secret and the writer key.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypedDict

import asyncpg
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from kavach.agent import guard as guard_mod
from kavach.agent import replies as R
from kavach.agent.trust_client import TrustClient, TrustUnavailable
from kavach.agent.understand import REASON_CHOICES, Understanding, understand
from kavach.common.contracts import Caller, Claim, Decision, ExecuteIn, ProposalIn, Verdict, VerdictOut, WriteTool
from kavach.events import EventBus
from kavach.store.client import NotFound, StoreClient, StoreUnavailable
from kavach.trust.policy import search as policy_search
from kavach.trust.rules import injection_flags, required_for

WRITE_INTENTS = {"refund": WriteTool.issue_refund, "return": WriteTool.create_return_pickup,
                 "change_address": WriteTool.update_address, "cancel": WriteTool.cancel_order}
CLAUSE_FOR = {WriteTool.issue_refund: 1, WriteTool.create_return_pickup: 1, WriteTool.update_address: 7, WriteTool.cancel_order: 8}
MAX_HISTORY = 12


class TurnState(TypedDict, total=False):
    conv: dict            # {channel, user_id, customer_id, name, lang, session}
    text: str
    media: list
    trace_id: str
    history: list
    pending: dict | None
    guard: dict
    u: dict
    orders: list
    order: dict | None
    shipment: dict | None
    courier_down: bool
    clauses: list
    photos: list
    returns: list
    refunds: list
    plan: list
    outcome: dict
    reply: str


class ApprovalState(TypedDict, total=False):
    approval_id: int
    trace_id: str
    conv: dict
    tool: str
    args: dict
    order: dict
    lang: str
    decision: dict
    result: dict


Send = Callable[[dict, str, str | None], Awaitable[None]]           # (conv, text, trace_id)
NotifySeller = Callable[[dict], Awaitable[None]]                     # approval card


@dataclass
class Deps:
    pool: asyncpg.Pool
    store: StoreClient
    trust: TrustClient
    bus: EventBus
    send: Send
    notify_seller: NotifySeller
    on_block: Callable[[dict, str, int | None], Awaitable[None]] | None = None   # alert calls: burst detection
    fetch_media: Callable[[dict], Awaitable[bytes | None]] | None = None          # photo check (None = check off)


def _lang(state: TurnState) -> str:
    return (state.get("u") or {}).get("lang") or state["conv"].get("lang") or "hinglish"


def build(deps: Deps, checkpointer: Any):
    bus = deps.bus

    # ───────────────────────── conversation nodes ─────────────────────────
    async def ingest(s: TurnState) -> dict:
        t0 = time.perf_counter()
        hist = (s.get("history") or []) + [{"role": "customer", "text": s["text"][:500]}]
        out: dict = {"history": hist[-MAX_HISTORY:], "order": None, "shipment": None, "courier_down": False, "photos": [],
                     "plan": [], "outcome": {}, "reply": "", "u": {}}
        await bus.emit(s["trace_id"], "ingest", "ok", t0, channel=s["conv"]["channel"],
                       media=len(s.get("media") or []), text=s["text"][:200])
        return out

    async def guard(s: TurnState) -> dict:
        t0 = time.perf_counter()
        g = guard_mod.score(s["text"])
        await bus.emit(s["trace_id"], "guard", "warn" if g.score >= 0.8 else "ok", t0,
                       guard_score=g.score, guard_tags=g.tags, model=g.model)
        return {"guard": {"score": g.score, "tags": g.tags, "model": g.model}}

    async def understand_node(s: TurnState) -> dict:
        t0 = time.perf_counter()
        cid = s["conv"]["customer_id"]
        try:
            orders = await deps.store.orders(cid, limit=10)
        except StoreUnavailable:
            orders = []
        pending = s.get("pending")
        has_photo = any(m.get("kind") == "image" for m in s.get("media") or [])
        if pending and pending.get("kind") == "need_photo" and has_photo:
            u = Understanding.model_validate({**pending["u"], "source": "fast_path"})
        elif pending and pending.get("kind") == "need_address" and len(s["text"].strip()) >= 6:
            u = Understanding.model_validate({**pending["u"], "new_address": s["text"].strip()[:300], "source": "fast_path"})
        else:
            u = await understand(s["text"], orders=orders, pending=pending, history=s.get("history") or [])
            if u.choice and pending and pending.get("kind") == "choose_order":
                opts = pending.get("options") or []
                if 1 <= u.choice <= len(opts):
                    u = Understanding.model_validate({**pending.get("u", {}), "order_id": opts[u.choice - 1], "source": "fast_path"})
        if pending and pending.get("kind") == "choose_reason" and u.intent in ("refund", "return", "other") and u.reason:
            u.intent = "refund" if u.intent == "other" else u.intent
            u.order_id = u.order_id or pending.get("order_id")
        await bus.emit(s["trace_id"], "understand", "ok" if u.source != "fallback" else "warn", t0,
                       intent=u.intent, order_id=u.order_id, lang=u.lang, source=u.source, provider=u.provider,
                       assertions=[a.model_dump() for a in u.customer_assertions], why_plan=u.why_plan,
                       tasks=1 + len(u.also))
        return {"u": u.model_dump(), "orders": orders, "pending": None}

    async def plan_read(s: TurnState) -> dict:
        t0 = time.perf_counter()
        u = Understanding.model_validate(s["u"])
        chosen = list(dict.fromkeys(u.plan))   # what the model decided to look up
        needs = {"where_is_order": ["get_order", "track_shipment"], "refund": ["get_order", "track_shipment", "search_policy", "get_photos"],
                 "return": ["get_order", "track_shipment", "search_policy", "get_photos"], "change_address": ["get_order", "search_policy"],
                 "cancel": ["get_order", "search_policy"], "policy_question": ["search_policy"],
                 "refund_status": ["refund_history"]}.get(u.intent, [])
        plan = list(chosen)
        added = [t for t in needs if t not in plan]   # safety floor: facts the verifier will demand anyway
        plan += added
        if not u.order_id and "get_order" in plan:
            plan.insert(0, "list_orders")
        await bus.emit(s["trace_id"], "plan", "ok", t0, plan=plan, intent=u.intent, chosen=chosen, added=added, why=u.why_plan)

        t1 = time.perf_counter()
        out: dict = {"plan": plan}
        deps.store.calls.clear()
        order = None
        if u.order_id and "get_order" in plan:
            try:
                order = await deps.store.order(u.order_id)
            except NotFound:
                order = None
            except StoreUnavailable:
                out["courier_down"] = True
        out["order"] = order
        mine = order is not None and order["customer_id"] == s["conv"]["customer_id"]
        if mine and order.get("awb") and "track_shipment" in plan:
            try:
                out["shipment"] = await deps.store.shipment(order["awb"])
            except StoreUnavailable:
                out["courier_down"] = True
        if "search_policy" in plan:
            try:
                out["clauses"] = await deps.store.policies()
            except StoreUnavailable:
                out["clauses"] = []
        if mine and u.intent in ("refund", "return"):
            try:
                out["returns"] = await deps.store.returns_for_order(order["id"])
            except StoreUnavailable:
                out["returns"] = []
        # Photos are evidence only for a refund/return on the customer's own order. Each one is checked (Phase 5-lite).
        if mine and u.intent in ("refund", "return"):
            await file_photos(s, order, u.reason)
        if mine and "get_photos" in plan:
            try:
                out["photos"] = await deps.store.photos(order["id"])
            except StoreUnavailable:
                out["photos"] = []
        if "refund_history" in plan:
            try:
                out["refunds"] = await deps.store.refunds_for_customer(s["conv"]["customer_id"], days=90)
            except StoreUnavailable:
                out["refunds"] = []
        await bus.emit(s["trace_id"], "read", "warn" if out.get("courier_down") else "ok", t1, calls=list(deps.store.calls))
        return out

    async def file_photos(s: TurnState, order: dict, reason: str | None) -> None:
        from kavach.agent import vision
        for m in s.get("media") or []:
            if m.get("kind") != "image":
                continue
            digest = hashlib.sha256((m.get("sha256") or m.get("url") or m.get("ref") or str(time.time())).encode()).hexdigest()[:16]
            if await deps.pool.fetchval("SELECT 1 FROM photos WHERE order_id = $1 AND phash = $2", order["id"], digest):
                continue                                    # same photo, same order: already filed and checked
            score, note = None, None
            if deps.fetch_media is not None:
                t0 = time.perf_counter()
                data = await deps.fetch_media(m)
                if data is None:
                    score, note = -1.0, "photo could not be downloaded"
                else:
                    chk = await vision.check(data, order["item"], reason)
                    score, note = chk.score, chk.note
                await bus.emit(s["trace_id"], "photo", "ok" if score >= 0.6 else "warn" if score < 0 or score >= 0.3 else "fail", t0,
                               score=round(score, 2))
            await deps.pool.execute("INSERT INTO photos(order_id, phash, source, media_type, ai_score, ai_note) VALUES ($1,$2,$3,$4,$5,$6)",
                                    order["id"], digest, s["conv"]["channel"], m.get("content_type", "image"), score, note)

    # ───────────────────────── act: decide, propose, verify, execute ─────────────────────────
    def _claims(tool: WriteTool, args: dict, u: Understanding, clauses: list, guard_tags: list[str], text: str) -> list[Claim]:
        kinds = sorted(required_for(tool, args), key=lambda k: k.value)
        claims: list[Claim] = []
        window_claim = next((a for a in u.customer_assertions if a.type == "window"), None)
        for k in kinds:
            if k.value == "policy":
                cid = 2 if (tool in (WriteTool.issue_refund, WriteTool.create_return_pickup) and args.get("reason") in ("damaged", "wrong_item")) else CLAUSE_FOR[tool]
                clause = next((c for c in clauses if c["id"] == cid), None)
                claims.append(Claim(kind="policy", source="policy", clause_id=cid, quote=clause["text"] if clause else ""))
            elif k.value == "temporal" and window_claim:
                claims.append(Claim(kind="temporal", source="customer", statement=window_claim.text))
            else:
                claims.append(Claim(kind=k.value, source="tool"))
        for a in u.customer_assertions:       # forward what the customer asserted so it is checked, not trusted
            if a.type == "authority":
                claims.append(Claim(kind="authority", source="customer", statement=a.text[:200]))
            elif a.type == "policy":
                claims.append(Claim(kind="policy", source="customer", statement=a.text[:200]))
        # safety net (also covers safe mode with no LLM): the rules guard saw an authority/policy claim
        if "AUTHORITY" in guard_tags and not any(c.kind.value == "authority" for c in claims):
            claims.append(Claim(kind="authority", source="customer", statement=text[:200]))
        if "POLICY_CLAIM" in guard_tags and not any(c.source.value == "customer" for c in claims if c.kind.value in ("temporal", "policy")):
            claims = [Claim(kind="temporal", source="customer", statement=text[:200]) if c.kind.value == "temporal" else c for c in claims]
        return claims

    async def act(s: TurnState) -> dict:
        """One message may hold two requests. The first runs normally; the second gets its own read + checks."""
        first = await act_one(s)
        u = Understanding.model_validate(s["u"])
        if not u.also or first.get("pending"):
            return first
        t = u.also[0]
        if t.intent == u.intent and (t.order_id or u.order_id) == u.order_id:
            return first
        u2 = Understanding.model_validate({**u.model_dump(), **t.model_dump(), "also": [], "plan": [], "customer_assertions": [],
                                           "amount_rupees": None, "choice": None})
        state = {**s, "u": u2.model_dump(), "pending": None}
        state.update(await plan_read(state))
        second = await act_one(state)
        merged = {**second, **first, "reply": f"{first.get('reply', '')}\n\n{second.get('reply', '')}".strip()}
        if not first.get("outcome") and second.get("outcome"):
            merged["outcome"] = second["outcome"]
        if not first.get("pending") and second.get("pending"):
            merged["pending"] = second["pending"]
        return merged

    async def act_one(s: TurnState) -> dict:
        u = Understanding.model_validate(s["u"])
        lang, conv, order = _lang(s), s["conv"], s.get("order")
        mine = order is not None and order["customer_id"] == conv["customer_id"]
        trace = s["trace_id"]

        def reply(text: str, **extra) -> dict:
            return {"reply": text, **extra}

        # read-only intents
        if u.intent == "greeting":
            return reply(R.greeting(conv.get("name", ""), s.get("orders") or [], lang))
        if u.intent == "refund_status":
            return reply(R.refund_status(s.get("refunds") or [], s.get("orders") or [], u.order_id, lang))
        if u.intent == "talk_to_human":
            await deps.notify_seller({"kind": "human", "conv": conv, "trace_id": trace,
                                      "summary": f"{conv.get('name')} asked for a person. Last message: {s['text'][:200]}"})
            return reply(R.say("human", lang))
        if u.intent == "policy_question":
            hits = policy_search(s.get("clauses") or [], u.policy_query or s["text"], k=1)
            if hits:
                c = hits[0]
                return reply(R.say("policy", lang, text=c["text_hinglish"] if lang == "hinglish" and c.get("text_hinglish") else c["text"]))
            return reply(R.say("other", lang))
        if u.intent == "other":
            return reply(R.say("other", lang))

        # instructions aimed at the agent itself ("ignore your rules…") are refused outright and flagged
        if "INJECTION" in (s.get("guard") or {}).get("tags", []) and u.intent in WRITE_INTENTS:
            await deps.notify_seller({"kind": "injection", "conv": conv, "trace_id": trace,
                                      "summary": f"{conv.get('name')} sent instructions aimed at the agent: \"{s['text'][:160]}\""})
            await bus.emit(trace, "route", "fail", None, verdict="BLOCK", reasons=["instruction_to_agent"])
            if deps.on_block is not None:
                await deps.on_block(conv, trace, u.order_id)
            return reply({"en": "I can't follow instructions like that. I only act on your orders and our written policy. If you need something specific, tell me the order and the problem.",
                          "hinglish": "Aise instructions main follow nahi karta. Main sirf aapke orders aur hamari likhi policy ke hisaab se kaam karta hoon. Kisi order mein dikkat hai to order aur problem bataiye.",
                          "hi": "ऐसे निर्देश मैं नहीं मानता। मैं सिर्फ़ आपके ऑर्डर और हमारी लिखी नीति के हिसाब से काम करता हूँ। किसी ऑर्डर में दिक़्क़त हो तो ऑर्डर और समस्या बताइए।"}.get(lang, ""),
                         outcome={"verdict": "BLOCK", "reasons": ["instruction_to_agent"]})

        # everything else needs an order
        if not u.order_id:
            orders = s.get("orders") or []
            if u.intent == "where_is_order":
                moving = [o for o in orders if o["status"] in ("shipped",)]
                if len(moving) == 1:
                    u.order_id = moving[0]["id"]
            if not u.order_id:
                if not orders:
                    return reply(R.say("no_orders", lang))
                opts = orders[:5]
                lines = "\n".join(f"{i}. {o['item']} (order {o['id']})" for i, o in enumerate(opts, 1))
                return reply(R.say("choose_order", lang, options=lines),
                             pending={"kind": "choose_order", "intent": u.intent, "options": [o["id"] for o in opts], "u": u.model_dump()})
            return await plan_again(s, u)
        if order is None and not s.get("courier_down"):
            return reply(R.say("unknown_order", lang, oid=u.order_id))
        if s.get("courier_down") and order is None:
            await deps.notify_seller({"kind": "courier_down", "conv": conv, "trace_id": trace, "summary": f"Store/courier unreachable while {conv.get('name')} asked about order {u.order_id}."})
            return reply(R.say("courier_down", lang))

        if u.intent == "where_is_order":
            if not mine:
                return reply(R.say("not_yours", lang, oid=u.order_id))
            ship = s.get("shipment")
            if s.get("courier_down"):
                await deps.notify_seller({"kind": "courier_down", "conv": conv, "trace_id": trace,
                                          "summary": f"Courier API down; {conv.get('name')} asked where order {order['id']} is."})
                return reply(R.say("courier_down", lang))
            if order["status"] in ("placed", "packed") or not ship:
                return reply(R.say("status_not_shipped", lang, item=order["item"], oid=order["id"], status=order["status"]))
            if ship["status"] == "delivered":
                rel, date = R.days_ago(ship.get("delivered_at"), lang)
                return reply(R.say("status_delivered", lang, item=order["item"], oid=order["id"], days=rel, date=date))
            where = (ship.get("events") or [{}])[-1].get("where", "the hub")
            return reply(R.say("status_transit", lang, item=order["item"], oid=order["id"], courier=ship.get("courier", "courier"), where=where))

        # a refund with no reason: ask what happened (fixed numbered options, nothing invented)
        # Only for ordinary messages: anything with a claim of authority, pressure, a stated amount or a policy claim
        # goes straight to the verifier so it is checked and recorded, not softened into a question.
        risky = (bool((s.get("guard") or {}).get("tags")) or bool(u.customer_assertions) or u.amount_rupees is not None
                 or bool(injection_flags(order.get("note") or "")))          # a hidden instruction in the record itself
        if u.intent == "refund" and u.reason is None and mine and order["status"] == "delivered" and not s.get("media") and not risky:
            return reply(R.say("choose_reason", lang, item=order["item"], oid=order["id"]),
                         pending={"kind": "choose_reason", "order_id": order["id"], "u": u.model_dump()})

        # write intents → build a proposal
        tool = WRITE_INTENTS[u.intent]
        converted = False
        # Seller policy, like real Indian e-commerce: an instant refund needs a damaged or wrong item (with a photo).
        # "Didn't like it" / no reason -> book a return pickup, refund after the item is back.
        # "Never received it" on a delivered order -> the seller investigates.
        if tool is WriteTool.issue_refund and u.reason not in ("damaged", "wrong_item"):
            if u.reason == "not_delivered" and (s.get("shipment") or {}).get("status") == "delivered" and mine:
                await deps.notify_seller({"kind": "dispute", "conv": conv, "trace_id": trace,
                                          "summary": f"{conv.get('name')} says order {order['id']} ({order['item']}) never arrived; courier shows delivered."})
                return reply({"en": f"Courier records show order {order['id']} as delivered. I've asked the seller to check with the courier; they'll get back to you.",
                              "hinglish": f"Courier ke record mein order {order['id']} delivered dikh raha hai. Maine seller ko courier se check karne ko bol diya hai, woh aapko batayenge.",
                              "hi": f"कूरियर के रिकॉर्ड में ऑर्डर {order['id']} डिलीवर दिख रहा है। मैंने विक्रेता से कूरियर से जाँच करने को कहा है, वे आपको बताएँगे।"}.get(lang, ""),
                             outcome={"verdict": "ESCALATE", "reasons": ["delivery_dispute"]})
            if u.reason != "not_delivered":
                tool, converted = WriteTool.create_return_pickup, True
        if tool is WriteTool.update_address and not u.new_address:
            return reply({"en": "Please send the new full address.", "hinglish": "Naya poora address bhej dijiye.",
                          "hi": "नया पूरा पता भेज दीजिए।"}.get(lang, "Naya poora address bhej dijiye."),
                         pending={"kind": "need_address", "order_id": order["id"], "u": u.model_dump()})
        reason = u.reason if u.reason in ("damaged", "wrong_item", "changed_mind", "other") else ("other" if u.reason else "changed_mind")
        if tool is WriteTool.issue_refund:
            left = order["paid_paise"] - order["refunded_paise"]
            amount = u.amount_rupees * 100 if u.amount_rupees else left
            args = {"order_id": order["id"], "amount_paise": max(1, amount), "reason": reason}
        elif tool is WriteTool.create_return_pickup:
            args = {"order_id": order["id"], "reason": reason}
        elif tool is WriteTool.update_address:
            args = {"order_id": order["id"], "new_address": u.new_address}
        else:
            args = {"order_id": order["id"]}

        # already in progress? explain instead of booking it again (and tell the seller if the customer is pressing)
        if mine and tool is WriteTool.create_return_pickup and s.get("returns"):
            r0 = s["returns"][0]
            rel, _ = R.days_ago(r0.get("created_at"), lang)
            pressing = "PRESSURE" in (s.get("guard") or {}).get("tags", []) or any(
                w in s["text"].lower() for w in ("urgent", "emergency", "abhi", "jaldi", "right now", " rn", "now", "turant"))
            if pressing:
                await deps.notify_seller({"kind": "human", "conv": conv, "trace_id": trace,
                                          "summary": f"{conv.get('name')} is pressing for the refund on order {order['id']} ({order['item']}); a return pickup is already booked."})
            extra = {"en": " I've told the seller you need it urgently; they'll get back to you." if pressing else " Reply \"human\" if you need the seller.",
                     "hi": " मैंने विक्रेता को बता दिया है कि आपको जल्दी चाहिए।" if pressing else " विक्रेता से बात करनी हो तो \"human\" लिखिए।"
                     }.get(lang, " Maine seller ko bata diya hai ki aapko jaldi chahiye, woh sampark karenge." if pressing else " Seller se baat karni ho to \"human\" likhiye.")
            msg = {"en": f"A return pickup for order {order['id']} ({order['item']}) is already booked ({rel}). The refund is processed once the item is picked up and checked.",
                   "hi": f"ऑर्डर {order['id']} ({order['item']}) का रिटर्न पिकअप पहले से बुक है ({rel})। सामान पिकअप और जाँच के बाद रिफ़ंड हो जाएगा।"
                   }.get(lang, f"Order {order['id']} ({order['item']}) ka return pickup pehle se book hai ({rel}). Item pickup aur check ke baad refund ho jayega.")
            return reply(msg + extra, outcome={"verdict": "NONE", "reasons": ["already_in_progress"]})
        if mine and tool is WriteTool.issue_refund and order["refunded_paise"] >= order["paid_paise"]:
            return reply({"en": f"Order {order['id']} ({order['item']}) has already been refunded in full ({R.rs(order['refunded_paise'])}).",
                          "hi": f"ऑर्डर {order['id']} ({order['item']}) का पूरा रिफ़ंड ({R.rs(order['refunded_paise'])}) पहले ही हो चुका है।"
                          }.get(lang, f"Order {order['id']} ({order['item']}) ka poora refund ({R.rs(order['refunded_paise'])}) pehle hi ho chuka hai."),
                         outcome={"verdict": "NONE", "reasons": ["already_refunded"]})

        # self-check before asking: a damage claim without a photo would only be blocked, so ask first
        if mine and reason in ("damaged", "wrong_item") and tool in (WriteTool.issue_refund, WriteTool.create_return_pickup) and not s.get("photos"):
            return reply(R.say("need_photo", lang, item=order["item"]),
                         pending={"kind": "need_photo", "order_id": order["id"], "u": u.model_dump()})

        t0 = time.perf_counter()
        prop = ProposalIn(trace_id=trace, tool=tool, args=args, claims=_claims(tool, args, u, s.get("clauses") or [], (s.get("guard") or {}).get("tags", []), s["text"]),
                          caller=Caller(customer_id=conv["customer_id"], channel=conv["channel"] if conv["channel"] != "web" else "web",
                                        channel_user_id=str(conv["user_id"])[:128]),
                          guard_score=(s.get("guard") or {}).get("score"), flags=[f"guard:{t}" for t in (s.get("guard") or {}).get("tags", [])][:5])
        await bus.emit(trace, "propose", "ok", t0, tool=tool.value, amount_paise=args.get("amount_paise"),
                       claims=[c.kind.value + ("·customer" if c.source.value == "customer" else "") for c in prop.claims])
        t1 = time.perf_counter()
        try:
            v = await deps.trust.verify(prop)
        except TrustUnavailable:
            await bus.emit(trace, "verify", "fail", t1, error="trust service unavailable")
            return reply(R.say("courier_down", lang))
        await bus.emit(trace, "verify", {"ALLOW": "ok", "ESCALATE": "warn", "BLOCK": "fail"}[v.verdict.value], t1,
                       claims=[r.model_dump(mode="json") for r in v.results], verdict=v.verdict.value)
        await bus.emit(trace, "route", {"ALLOW": "ok", "ESCALATE": "warn", "BLOCK": "fail"}[v.verdict.value], None,
                       verdict=v.verdict.value, reasons=v.reasons, approval_id=v.approval_id, risk=v.risk.model_dump())
        return await _route({**s, "converted_refund": converted}, tool, args, order, v, lang)

    async def plan_again(s: TurnState, u: Understanding) -> dict:
        """The order was inferred after planning (e.g. the only parcel in transit): read it, then act."""
        state = {**s, "u": u.model_dump()}
        state.update(await plan_read(state))
        return {**await act(state), "u": u.model_dump(), "order": state.get("order"), "shipment": state.get("shipment")}

    async def _route(s: TurnState, tool: WriteTool, args: dict, order: dict, v: VerdictOut, lang: str) -> dict:
        conv, trace = s["conv"], s["trace_id"]
        outcome = {"verdict": v.verdict.value, "reasons": v.reasons, "proposal_id": v.proposal_id, "tool": tool.value, "args": args}
        if v.verdict is Verdict.ALLOW:
            t0 = time.perf_counter()
            res = await deps.trust.execute(ExecuteIn(proposal_id=v.proposal_id, tool=tool, args=args, token=v.token or ""))
            await bus.emit(trace, "execute", "ok" if res.status in ("executed", "already_executed") else "fail", t0,
                           result=res.status, reason=res.reason, tool=tool.value)
            outcome["executed"] = res.status
            if res.status in ("executed", "already_executed"):
                text = done_text(tool, args, order, lang)
                if s.get("converted_refund"):
                    text += {"en": " Your refund is processed once the item is picked up and checked.",
                             "hinglish": " Item pickup aur check hone ke baad refund process ho jayega.",
                             "hi": " सामान पिकअप और जाँच के बाद रिफ़ंड हो जाएगा।"}.get(lang, "")
                text += R.records_line(order, s.get("shipment"), lang)
                return {"reply": text, "outcome": outcome}
            if (res.reason or "").startswith("kill_switch"):
                return {"reply": R.say("frozen", lang), "outcome": outcome}
            return {"reply": R.say("courier_down", lang), "outcome": outcome}
        if v.verdict is Verdict.ESCALATE:
            if v.reasons == ["source_unavailable"] or not v.approval_id:
                await deps.notify_seller({"kind": "courier_down", "conv": conv, "trace_id": trace,
                                          "summary": f"Could not verify {tool.value} on order {order['id']}: a source is down."})
                return {"reply": R.say("courier_down", lang), "outcome": outcome}
            await start_approval(v.approval_id, trace, conv, tool.value, args, order, lang, v.reasons)
            key = next((r for r in v.reasons if r in R.ESC_WHY), "guard_flag")
            why = R.phrase(R.ESC_WHY, key, lang, limit=R.rs(v.risk.auto_limit_paise or 50000))
            what = R.phrase(R.WHAT, tool.value, lang, amount=R.rs(args.get("amount_paise", 0)))
            return {"reply": R.say("escalated", lang, what=what, oid=order["id"], why=why) + R.records_line(order, s.get("shipment"), lang),
                    "outcome": outcome}
        # BLOCK: explain the most important reasons in plain words, quoting the real policy when relevant
        if deps.on_block is not None:
            await deps.on_block(conv, trace, order.get("id"))
        res = {r.kind.value: r for r in v.results}
        days = None
        if "temporal" in res:
            import re as _re
            m = _re.match(r"(\d+) day", res["temporal"].why)
            days = m.group(1) if m else "?"
        order_of = ["ownership", "authority", "temporal", "policy", "duplicate", "monetary", "eligibility", "evidence", "state", "frequency", "channel_identity"]
        keys = [k for k in order_of if k in v.reasons or f"missing_{k}" in v.reasons][:2] or ["policy"]
        if "ownership" in keys:
            keys = ["ownership"]                         # not their order: nothing else about it is their business
        if "evidence" in keys and s.get("photos"):
            keys = ["evidence_photo" if k == "evidence" else k for k in keys]   # a photo came, it just doesn't show the problem
        why = "; ".join(R.phrase(R.WHY, k, lang, window=7, days=days, item=order["item"]) for k in keys)
        clause = ""
        if any(k in keys for k in ("temporal", "policy", "eligibility")):
            want = 3 if "eligibility" in keys else (2 if args.get("reason") in ("damaged", "wrong_item") else CLAUSE_FOR.get(tool, 1))
            c = next((c for c in (s.get("clauses") or []) if c["id"] == want), None)
            if c:
                clause = R.policy_quote(c, lang)
        mine = order["customer_id"] == conv["customer_id"]
        rec = R.records_line(order, s.get("shipment"), lang) if mine else ""
        return {"reply": R.say("blocked", lang, why=why, clause=clause, oid=order["id"], item=order["item"] if mine else "—") + rec, "outcome": outcome}

    async def respond(s: TurnState) -> dict:
        t0 = time.perf_counter()
        text = s.get("reply") or R.say("other", _lang(s))
        if (s.get("outcome") or {}).get("verdict") in ("ALLOW", "ESCALATE", "BLOCK"):
            text += R.ref_line(s["trace_id"], s["conv"].get("channel", "web"), _lang(s))   # every decision gets a reference
        await deps.send(s["conv"], text, s["trace_id"])
        hist = (s.get("history") or []) + [{"role": "agent", "text": text[:500]}]
        await bus.emit(s["trace_id"], "reply", "ok", t0, lang=_lang(s), chars=len(text))
        return {"history": hist[-MAX_HISTORY:], "reply": text}

    conv_g = StateGraph(TurnState)
    for name, fn in (("ingest", ingest), ("guard", guard), ("understand", understand_node), ("plan_read", plan_read),
                     ("act", act), ("respond", respond)):
        conv_g.add_node(name, fn)
    conv_g.add_edge(START, "ingest")
    conv_g.add_edge("ingest", "guard")
    conv_g.add_edge("guard", "understand")
    conv_g.add_edge("understand", "plan_read")
    conv_g.add_edge("plan_read", "act")
    conv_g.add_edge("act", "respond")
    conv_g.add_edge("respond", END)
    conversation = conv_g.compile(checkpointer=checkpointer)

    # ───────────────────────── approval graph ─────────────────────────
    async def await_seller(s: ApprovalState) -> dict:
        decision = interrupt({"approval_id": s["approval_id"], "tool": s["tool"], "args": s["args"]})
        return {"decision": decision}

    async def finish(s: ApprovalState) -> dict:
        d, trace, lang, order = s["decision"], s["trace_id"], s.get("lang", "hinglish"), s["order"]
        t0 = time.perf_counter()
        status, body = await deps.trust.decide(s["approval_id"], Decision.model_validate(d))
        if status != 200:
            await bus.emit(trace, "approve", "fail", t0, approval_id=s["approval_id"], detail=body.get("detail"))
            return {"result": {"status": "error", "detail": body.get("detail")}}
        v = VerdictOut.model_validate(body)
        await bus.emit(trace, "approve", "ok" if v.verdict is Verdict.ALLOW else "fail", t0,
                       approval_id=s["approval_id"], decision=d["decision"], verdict=v.verdict.value, reasons=v.reasons)
        tool = WriteTool(s["tool"])
        what = R.phrase(R.WHAT, s["tool"], lang, amount=R.rs(s["args"].get("amount_paise", 0)))
        if v.verdict is Verdict.ALLOW and v.token:
            args = dict(s["args"])
            if d.get("edited_amount_paise"):
                args["amount_paise"] = d["edited_amount_paise"]
            t1 = time.perf_counter()
            res = await deps.trust.execute(ExecuteIn(proposal_id=v.proposal_id, tool=tool, args=args, token=v.token))
            await bus.emit(trace, "execute", "ok" if res.status in ("executed", "already_executed") else "fail", t1,
                           result=res.status, reason=res.reason, tool=s["tool"])
            if res.status in ("executed", "already_executed"):
                await deps.send(s["conv"], R.say("approved_done", lang, done=done_text(tool, args, order, lang)), trace)
            elif (res.reason or "").startswith("kill_switch"):
                await deps.send(s["conv"], R.say("frozen", lang), trace)
            return {"result": {"status": res.status, "reason": res.reason}}
        await deps.send(s["conv"], R.say("rejected", lang, what=what, oid=order["id"]), trace)
        return {"result": {"status": "rejected", "reasons": v.reasons}}

    ap = StateGraph(ApprovalState)
    ap.add_node("await_seller", await_seller)
    ap.add_node("finish", finish)
    ap.add_edge(START, "await_seller")
    ap.add_edge("await_seller", "finish")
    ap.add_edge("finish", END)
    approvals = ap.compile(checkpointer=checkpointer)

    async def start_approval(approval_id: int, trace: str, conv: dict, tool: str, args: dict, order: dict, lang: str,
                             reasons: list[str] | None = None) -> None:
        cfg = {"configurable": {"thread_id": f"approval-{approval_id}"}}
        await approvals.ainvoke({"approval_id": approval_id, "trace_id": trace, "conv": conv, "tool": tool, "args": args,
                                 "order": {"id": order["id"], "item": order["item"], "cod": order.get("cod", False)}, "lang": lang}, cfg)
        await deps.notify_seller({"kind": "approval", "approval_id": approval_id, "conv": conv, "trace_id": trace,
                                  "tool": tool, "args": args, "order": {"id": order["id"], "item": order["item"]}, "reasons": reasons or []})

    return conversation, approvals


def done_text(tool: WriteTool, args: dict, order: dict, lang: str) -> str:
    if tool is WriteTool.issue_refund:
        method = {"en": "UPI", "hinglish": "UPI", "hi": "UPI"}[lang if lang in ("en", "hinglish", "hi") else "hinglish"]
        return R.say("done_refund", lang, amount=R.rs(args["amount_paise"]), item=order["item"], oid=order["id"], method=method)
    if tool is WriteTool.create_return_pickup:
        return R.say("done_return", lang, item=order["item"], oid=order["id"])
    if tool is WriteTool.update_address:
        return R.say("done_address", lang, oid=order["id"], address=args["new_address"])
    return R.say("done_cancel", lang, oid=order["id"], item=order["item"])


class Agent:
    """Facade used by the gateway: one lock per conversation so messages are handled in order."""

    def __init__(self, deps: Deps, checkpointer: Any):
        self.deps = deps
        self.conversation, self.approvals = build(deps, checkpointer)
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            if len(self._locks) > 10_000:
                self._locks = {k: v for k, v in self._locks.items() if v.locked()}
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def handle(self, conv: dict, text: str, media: list | None = None, trace_id: str | None = None) -> dict:
        trace = trace_id or f"tr_{uuid.uuid4().hex[:12]}"
        if conv.get("session"):
            self.deps.bus.bind(trace, conv["session"])
        key = f"conv:{conv['channel']}:{conv['user_id']}"
        payload = {"conv": conv, "text": text[:1000], "media": media or [], "trace_id": trace}
        async with self._lock(key):
            for attempt in (1, 2):           # one automatic retry for transient failures (e.g. a dropped DB connection)
                try:
                    out = await self.conversation.ainvoke(payload, {"configurable": {"thread_id": key}}, durability="exit")
                    break
                except Exception as e:  # noqa: BLE001
                    import logging as _lg; _lg.getLogger("kavach.agent").warning("turn failed (attempt %s): %r", attempt, e)
                    await self.deps.bus.emit(trace, "reply", "fail", None, error=type(e).__name__, attempt=attempt)
                    if attempt == 2:
                        sorry = {"en": "Sorry, that didn't go through on our side. Please send it again.",
                                 "hi": "माफ़ कीजिए, हमारी तरफ़ से गड़बड़ हुई। कृपया दोबारा भेजिए।"}.get(conv.get("lang"),
                                 "Maaf kijiye, hamari taraf se gadbad hui. Please dobara bhejiye.")
                        try:
                            await self.deps.send(conv, sorry, trace)
                        except Exception:  # noqa: BLE001
                            pass
                        return {"trace_id": trace, "reply": sorry, "outcome": {"error": type(e).__name__}, "intent": None}
                    await asyncio.sleep(0.5)
        return {"trace_id": trace, "reply": out.get("reply"), "outcome": out.get("outcome") or {}, "intent": (out.get("u") or {}).get("intent")}

    async def decide(self, approval_id: int, decision: dict) -> dict:
        """Resume the paused approval thread with the seller's decision (first decision wins)."""
        cfg = {"configurable": {"thread_id": f"approval-{approval_id}"}}
        async with self._lock(f"approval-{approval_id}"):
            st = await self.approvals.aget_state(cfg)
            if not st.next:
                return {"status": "not_pending"}
            out = await self.approvals.ainvoke(Command(resume=decision), cfg)
        return out.get("result") or {"status": "unknown"}

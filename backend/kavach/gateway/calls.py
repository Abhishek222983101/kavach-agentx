"""Seller alert calls (D-21): Kavach phones the seller for high-risk events, and can take the decision on the call.

Ported from Voight/decoy `callme.py` (same Twilio account and caller ID), adapted to Kavach:
  - triggers: instructions aimed at the agent; a burst of BLOCKs from one customer; a big (or hidden-instruction)
    refund still waiting for the seller after CALL_APPROVAL_WAIT_S. The last one asks "press 1 to approve, 2 to reject".
  - the number dialled comes ONLY from the environment (CALL_TO). Nothing a customer sends can change it.
  - cost and noise: test mode by default (CALL_DRY_RUN=1 builds the call and dials nothing), CALL_DAILY_CAP per day,
    CALL_TOTAL_CAP overall, one call per CALL_COOLDOWN_MIN (alerts during the cooldown are counted and mentioned in
    the next call), optional quiet hours (IST), 35 s limit, inline TwiML (nothing to host for the message itself).
  - the key-press webhook is checked twice: Twilio's signature over the exact URL, and our own per-approval token.
  - our own automated sessions (test_/verify_/eval_) never ring anything.
Every call (or why it was not placed) is written to the tamper-proof audit log and shown on the decision's receipt.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import hmac
import logging
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Awaitable, Callable
from xml.sax.saxutils import escape, quoteattr
from zoneinfo import ZoneInfo

import httpx

from kavach.gateway.outbound import is_test_session

log = logging.getLogger("kavach.calls")
IST = ZoneInfo("Asia/Kolkata")
API = "https://api.twilio.com/2010-04-01"
MAX_WORDS = 90                                  # about 35 s of speech
VOICE = 'voice="Polly.Aditi" language="en-IN"'

Transport = Callable[[str, str, dict | None], Awaitable[dict]]


def spoken_rupees(paise: int | None) -> str:
    r = (paise or 0) // 100
    return f"{r:,} rupees"


def _mask(n: str) -> str:
    d = re.sub(r"\D", "", n or "")
    return f"+{d[:2]} ****{d[-4:]}" if len(d) >= 8 else "not set"


class SellerCalls:
    def __init__(self, pool, bus, *, public_base_url: str, transport: Transport | None = None, env: dict | None = None,
                 decide: Callable[[int, dict], Awaitable[dict]] | None = None,
                 still_pending: Callable[[int], Awaitable[bool]] | None = None):
        e = env if env is not None else os.environ
        self.pool, self.bus = pool, bus
        self.sid, self.token = e.get("TWILIO_ACCOUNT_SID", ""), e.get("TWILIO_AUTH_TOKEN", "")
        self.caller_id, self.to = e.get("TWILIO_CALLER_ID", ""), e.get("CALL_TO", "")
        self.enabled = e.get("CALLS_ENABLED", "0") == "1" and bool(self.sid and self.token and self.caller_id and self.to)
        self.dry_run = e.get("CALL_DRY_RUN", "1") != "0"
        self.daily_cap = int(e.get("CALL_DAILY_CAP", "3"))
        self.total_cap = int(e.get("CALL_TOTAL_CAP", "10"))
        self.cooldown_s = int(e.get("CALL_COOLDOWN_MIN", "30")) * 60
        self.approval_wait_s = int(e.get("CALL_APPROVAL_WAIT_S", "120"))
        self.big_paise = int(e.get("CALL_BIG_REFUND_PAISE", "200000"))
        self.burst_n, self.burst_window_s = int(e.get("CALL_BURST_N", "3")), int(e.get("CALL_BURST_WINDOW_MIN", "10")) * 60
        q = e.get("CALL_QUIET_HOURS", "")                       # e.g. "23-8" (IST); empty = no quiet hours
        self.quiet = tuple(int(x) for x in q.split("-")) if re.fullmatch(r"\d{1,2}-\d{1,2}", q) else None
        self.base = public_base_url.rstrip("/")
        self.transport = transport or self._http
        self.decide = decide
        self.still_pending = still_pending
        self._lock = asyncio.Lock()
        self._blocks: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self._burst_called: dict[str, float] = {}
        self._tasks: set = set()
        self.last: dict | None = None

    # ───────────── shared helpers ─────────────
    async def _http(self, method: str, url: str, data: dict | None) -> dict:
        async with httpx.AsyncClient(timeout=20, auth=(self.sid, self.token)) as c:
            r = await (c.post(url, data=data) if method == "POST" else c.get(url))
        if r.status_code >= 400:
            raise RuntimeError(f"twilio {r.status_code}: {r.json().get('message', '')[:120] if r.headers.get('content-type', '').startswith('application/json') else ''}")
        return r.json()

    async def _count(self, key: str) -> int:
        return int(await self.pool.fetchval("SELECT coalesce((SELECT n FROM usage_counters WHERE key = $1), 0)", key))

    async def _bump(self, key: str, by: int = 1) -> None:
        await self.pool.execute("""INSERT INTO usage_counters(key, n) VALUES ($1, $2)
                                   ON CONFLICT (key) DO UPDATE SET n = usage_counters.n + $2""", key, by)

    async def _set(self, key: str, value: int) -> None:
        await self.pool.execute("""INSERT INTO usage_counters(key, n) VALUES ($1, $2)
                                   ON CONFLICT (key) DO UPDATE SET n = $2""", key, value)

    def _today(self) -> str:
        return datetime.now(IST).strftime("%Y-%m-%d")

    def _quiet_now(self) -> bool:
        if not self.quiet:
            return False
        h, (a, b) = datetime.now(IST).hour, self.quiet
        return (a <= h or h < b) if a > b else (a <= h < b)

    def token_for(self, approval_id: int) -> str:
        return hmac.new(self.token.encode(), f"kavach-call:{approval_id}".encode(), hashlib.sha256).hexdigest()[:32]

    async def view(self) -> dict:
        return {"enabled": self.enabled, "test_mode": self.dry_run, "to": _mask(self.to), "max_seconds": 35,
                "daily_cap": self.daily_cap, "total_cap": self.total_cap, "cooldown_min": self.cooldown_s // 60,
                "calls_today": await self._count(f"calls:{self._today()}"), "calls_total": await self._count("calls:total"),
                "quiet_hours_ist": f"{self.quiet[0]}:00–{self.quiet[1]}:00" if self.quiet else None, "last": self.last}

    # ───────────── the one place a call is placed ─────────────
    async def place(self, kind: str, script: str, trace_id: str | None, *, gather_for: int | None = None) -> dict:
        """Decide whether to ring, then ring (or not) and record why. Never raises."""
        try:
            async with self._lock:
                result = await self._place(kind, script, trace_id, gather_for)
        except Exception as e:  # noqa: BLE001 - an alert problem must never break the conversation
            log.warning("seller call failed: %s", type(e).__name__)
            result = {"action": "error", "error": type(e).__name__}
        self.last = {"kind": kind, "action": result["action"], "at": int(time.time())}
        if trace_id:
            await self.bus.emit(trace_id, "alert", "warn" if result["action"] in ("called", "dry_run") else "ok", None,
                                kind=kind, result=result["action"], call_sid=result.get("sid"))
        try:
            await self.pool.execute("SELECT audit_append($1, $2, $3::jsonb)", "seller_call",
                                    f"{kind}: {result['action']}" + (f" (approval {gather_for})" if gather_for else ""),
                                    json.dumps({"trace_id": trace_id or "", "call_sid": result.get("sid") or ""}))
        except Exception:  # noqa: BLE001
            log.warning("could not audit the call")
        return result

    async def _place(self, kind: str, script: str, trace_id: str | None, gather_for: int | None) -> dict:
        if not self.enabled:
            return {"action": "off"}
        now = int(time.time())
        if self._quiet_now():
            await self._bump("calls:held")
            return {"action": "quiet_hours"}
        if now - await self._count("calls:last_at") < self.cooldown_s:
            await self._bump("calls:held")
            return {"action": "held"}
        if await self._count(f"calls:{self._today()}") >= self.daily_cap or await self._count("calls:total") >= self.total_cap:
            return {"action": "cap"}
        held = await self._count("calls:held")
        if held:
            script += f" Also, {held} more {'alert' if held == 1 else 'alerts'} came in since my last call. They are in your seller console."
        words = script.split()
        script = " ".join(words[:MAX_WORDS])
        twiml = self.twiml(script, gather_for)
        if self.dry_run:
            log.info("seller call (test mode, not dialled) [%s]: %s", kind, script)
            return {"action": "dry_run", "script": script}
        call = await self.transport("POST", f"{API}/Accounts/{self.sid}/Calls.json",
                                    {"To": self.to, "From": self.caller_id, "Twiml": twiml, "TimeLimit": "35", "Timeout": "25",
                                     "Record": "true"})                 # so anyone can replay the real call from the receipt
        await self._bump(f"calls:{self._today()}")
        await self._bump("calls:total")
        await self._set("calls:last_at", now)
        await self._set("calls:held", 0)
        log.info("seller call placed [%s] %s", kind, call.get("sid"))
        return {"action": "called", "sid": call.get("sid"), "script": script}

    def twiml(self, script: str, gather_for: int | None) -> str:
        say = f"<Say {VOICE}>{escape(script)}</Say>"
        if gather_for is None:
            return f"<Response>{say}<Say {VOICE}>Goodbye.</Say></Response>"
        action = f"{self.base}/webhooks/twilio/voice?aid={gather_for}&t={self.token_for(gather_for)}"
        return (f"<Response><Gather numDigits=\"1\" timeout=\"8\" action={quoteattr(action)} method=\"POST\">{say}</Gather>"
                f"<Say {VOICE}>No key pressed. The request stays in your seller console. Goodbye.</Say></Response>")

    # ───────────── triggers ─────────────
    async def on_card(self, card: dict) -> None:
        """Called for every seller card. Decides which ones are worth a phone call."""
        conv = card.get("conv") or {}
        if is_test_session(conv):
            return
        kind, trace = card.get("kind"), card.get("trace_id")
        if kind == "injection":
            await self.place("injection", "Hello, this is Kavach, your shop's support agent. A customer just sent me hidden "
                                          "instructions, trying to make me break your rules. I refused, and nothing was paid. "
                                          "The message is in your seller console.", trace)
        elif kind == "approval":
            amount = (card.get("args") or {}).get("amount_paise") or 0
            hidden = "instruction_in_record" in (card.get("reasons") or [])
            if amount >= self.big_paise or hidden:
                self._later(self._approval_reminder(card, hidden))

    async def on_block(self, conv: dict, trace_id: str, order_id: int | None) -> None:
        """Count BLOCKs per customer; a burst means someone is probing the agent."""
        if is_test_session(conv):
            return
        who = str(conv.get("customer_id") or conv.get("user_id"))
        now = time.time()
        q = self._blocks[who]
        q.append(now)
        recent = [t for t in q if now - t <= self.burst_window_s]
        if len(recent) >= self.burst_n and now - self._burst_called.get(who, 0) > 3600:
            self._burst_called[who] = now
            await self.place("burst", f"Hello, this is Kavach. One customer has made {len(recent)} refund or return requests "
                                      f"in the last few minutes that did not match your records"
                                      + (f", the latest on order {order_id}" if order_id else "") +
                                      ". All of them were blocked, and nothing was paid. You may want to look at your seller console.",
                             trace_id)

    def _later(self, coro) -> None:
        t = asyncio.create_task(coro)
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)

    async def _approval_reminder(self, card: dict, hidden: bool) -> None:
        await asyncio.sleep(self.approval_wait_s)
        aid = card.get("approval_id")
        if aid is None or (self.still_pending and not await self.still_pending(int(aid))):
            return                                              # the seller already decided on Telegram/WhatsApp/console
        args, order = card.get("args") or {}, card.get("order") or {}
        what = f"A {spoken_rupees(args['amount_paise'])} refund" if args.get("amount_paise") else "A " + str(card.get("tool", "request")).replace("_", " ")
        why = ("The order record contains a hidden instruction, so I need you to check it." if hidden
               else "It is above your limit for automatic refunds.")
        script = (f"Hello, this is Kavach. {what} on order {order.get('id')}, {order.get('item', '')}, is waiting for you. "
                  f"{why} The records check out. Press 1 to approve, or 2 to reject. To decide later, just hang up.")
        await self.place("approval", script, card.get("trace_id"), gather_for=int(aid))

    async def call_now(self, approval: dict, order: dict) -> dict:
        """The seller asked for the call right now (seller console button). Same script, same caps."""
        args = approval.get("args") or {}
        what = f"A {spoken_rupees(args['amount_paise'])} refund" if args.get("amount_paise") else "A " + str(approval.get("tool", "request")).replace("_", " ")
        script = (f"Hello, this is Kavach. {what} on order {order.get('id')}, {order.get('item', '')}, is waiting for you. "
                  f"The records check out. Press 1 to approve, or 2 to reject. To decide later, just hang up.")
        return await self.place("approval", script, approval.get("trace_id"), gather_for=int(approval["id"]))

    _audio: dict[str, bytes] = {}

    async def audio(self, call_sid: str) -> bytes | None:
        """The recording of a call Kavach placed (only those: checked against the audit log)."""
        if not re.fullmatch(r"CA[0-9a-f]{32}", call_sid):
            return None
        if call_sid in self._audio:
            return self._audio[call_sid]
        known = await self.pool.fetchval("SELECT 1 FROM audit_log WHERE event = 'seller_call' AND payload->>'call_sid' = $1", call_sid)
        if not known or not self.sid:
            return None
        recs = await self.transport("GET", f"{API}/Accounts/{self.sid}/Calls/{call_sid}/Recordings.json", None)
        items = recs.get("recordings") or []
        if not items:
            return None
        async with httpx.AsyncClient(timeout=20, auth=(self.sid, self.token), follow_redirects=True) as c:
            r = await c.get(f"{API}/Accounts/{self.sid}/Recordings/{items[0]['sid']}.mp3")
        if r.status_code != 200 or len(r.content) > 3_000_000:
            return None
        if len(self._audio) > 30:
            self._audio.clear()
        self._audio[call_sid] = r.content
        return r.content

    # ───────────── the key press ─────────────
    async def on_key(self, approval_id: int, token: str, digits: str) -> str:
        """Returns TwiML to speak back. Signature and token are checked by the caller (route)."""
        if not hmac.compare_digest(token, self.token_for(approval_id)):
            return f"<Response><Say {VOICE}>Sorry, this request could not be verified. Goodbye.</Say></Response>"
        if digits not in ("1", "2") or self.decide is None:
            return f"<Response><Say {VOICE}>No decision taken. It stays in your seller console. Goodbye.</Say></Response>"
        res: dict[str, Any] = await self.decide(approval_id, {"decision": "approve" if digits == "1" else "reject", "decided_via": "phone"})
        st = res.get("status")
        if st == "not_pending":
            msg = "This request was already decided. Nothing changed. Goodbye."
        elif st in ("executed", "already_executed"):
            msg = "Approved. Kavach re-checked the records and completed it. The customer has been told. Goodbye."
        elif st == "rejected":
            msg = "Rejected. The customer has been told politely. Goodbye."
        else:
            msg = "Kavach re-checked the records and could not complete it, so nothing was paid. Details are in your seller console. Goodbye."
        return f"<Response><Say {VOICE}>{escape(msg)}</Say></Response>"


# ───────────── wiring ─────────────
from fastapi import APIRouter, HTTPException, Request, Response  # noqa: E402

router = APIRouter()


@router.post("/webhooks/twilio/voice")
async def voice_key(request: Request, aid: int, t: str) -> Response:
    """The seller pressed a key during an alert call. Twilio signs the exact URL (with our token) and the form."""
    calls: SellerCalls | None = getattr(request.app.state, "calls", None)
    if calls is None or not calls.enabled:
        raise HTTPException(404, "calls are not configured")
    from twilio.request_validator import RequestValidator
    form = dict(await request.form())
    url = f"{calls.base}/webhooks/twilio/voice?{request.url.query}"
    if not RequestValidator(calls.token).validate(url, form, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "bad Twilio signature")
    twiml = await calls.on_key(aid, t, str(form.get("Digits", ""))[:1])
    return Response(twiml, media_type="application/xml")


async def setup(app) -> None:
    st = app.state

    async def still_pending(approval_id: int) -> bool:
        try:
            return any(int(a["id"]) == approval_id for a in await st.trust.approvals("pending"))
        except Exception:  # noqa: BLE001 - if unsure, don't ring
            return False

    st.calls = SellerCalls(st.pool, st.bus, public_base_url=st.public_base_url, decide=st.agent.decide, still_pending=still_pending)
    st.out.calls = st.calls
    st.agent.deps.on_block = st.calls.on_block
    if st.calls.enabled:
        st.channels_started.append("calls:" + ("test-mode" if st.calls.dry_run else "live"))

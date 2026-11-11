"""The trust service: verifier + router + token signer + executor (ARCH §9.4–§9.5, D-15).

It is the only process holding VERDICT_SECRET and the store's writer key. The agent process can only
*propose*; this service decides and, with a valid signed verdict, acts.

    verify(proposal)          -> ALLOW (+token) | ESCALATE (+approval id) | BLOCK
    decide(approval, choice)  -> re-verify, then APPROVED (+token) | rejected | BLOCK
    execute(token, args)      -> executed once | already_executed | refused(reason)

Every step is persisted (proposals, verdicts, approvals, executions), emitted as an event for the live
X-ray, and appended to the hash-chained audit log.
"""
from __future__ import annotations

import asyncio
import secrets
import time
from datetime import datetime, timezone
from typing import Any

import asyncpg
from pydantic import ValidationError

from kavach.common.canonical import args_hash
from kavach.common.contracts import (
    ARGS_MODEL, Claim, ClaimResult, Decision, ExecuteIn, ExecuteOut, ProposalIn, Risk, Verdict, VerdictOut, WriteTool,
)
from kavach.store.client import NotFound, StoreClient, StoreRefused, StoreUnavailable
from kavach.trust import tokens
from kavach.trust.claims import Facts, check, rupees
from kavach.trust.router import decide
from kavach.trust.rules import EXPECTED_STATE, injection_flags, required_for

HUMAN_CLEARED = {"over_auto_limit", "over_hard_cap", "refund_frequency", "guard_flag", "instruction_in_record"}


class TrustError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


class TrustService:
    def __init__(self, pool: asyncpg.Pool, store: StoreClient, secret: str, *, allow_ttl_s: int = 60,
                 approved_ttl_s: int = 86400, daily_write_cap: int = 200, daily_refund_cap_paise: int = 5_000_000):
        if len(secret) < 32:
            raise ValueError("VERDICT_SECRET must be at least 32 characters")
        self.pool, self.store, self._secret = pool, store, secret
        self.allow_ttl_s, self.approved_ttl_s = allow_ttl_s, approved_ttl_s
        self.daily_write_cap, self.daily_refund_cap_paise = daily_write_cap, daily_refund_cap_paise

    # ───────────────────────── helpers ─────────────────────────
    async def _event(self, conn: asyncpg.Connection, trace: str, stage: str, status: str, t0: float, payload: dict) -> None:
        await conn.execute("INSERT INTO events(trace_id, stage, status, t_ms, payload) VALUES ($1,$2,$3,$4,$5::jsonb)",
                           trace, stage, status, int((time.perf_counter() - t0) * 1000), payload)

    @staticmethod
    async def _audit(conn: asyncpg.Connection, event: str, summary: str, payload: dict) -> None:
        await conn.fetchval("SELECT audit_append($1, $2, $3::jsonb)", event, summary, payload)

    async def _facts(self, p: ProposalIn, args: dict) -> tuple[Facts, bool]:
        """Re-fetch everything from the system of record. Returns (facts, source_unavailable)."""
        f = Facts(tool=p.tool, args=args, caller=p.caller, order=None, now=datetime.now(timezone.utc))
        oid = args["order_id"]

        async def order_or_none() -> dict | None:
            try:
                return await self.store.order(oid)
            except NotFound:
                return None

        async def none() -> list:
            return []

        try:
            # round 1: independent reads in parallel
            settings, clauses, f.order = await asyncio.gather(self.store.settings(), self.store.policies(), order_or_none())
            f.settings, f.clauses = settings, {c["id"]: c for c in clauses}
            if f.order is None:
                return f, False
            # round 2: everything that needs the order, in parallel
            refund, ret = p.tool is WriteTool.issue_refund, p.tool in (WriteTool.issue_refund, WriteTool.create_return_pickup)
            need_ship = EXPECTED_STATE[p.tool] == "delivered" and f.order.get("awb")
            f.customer, f.shipment, f.order_refunds, f.customer_refunds_30d, f.photos = await asyncio.gather(
                self.store.customer(f.order["customer_id"]),
                self.store.shipment(f.order["awb"]) if need_ship else asyncio.sleep(0, None),
                self.store.refunds_for_order(oid) if refund else none(),
                self.store.refunds_for_customer(p.caller.customer_id, int(f.settings.get("freq_window_days", 30))) if refund else none(),
                self.store.photos(oid) if ret else none(),
            )
        except StoreUnavailable:
            return f, True
        return f, False

    def _risk(self, p: ProposalIn, f: Facts) -> Risk:
        amount = f.amount if p.tool is WriteTool.issue_refund else None
        auto = int(f.settings.get("auto_limit_paise", 50_000))
        cap = int(f.settings.get("hard_cap_paise", 200_000))
        flags = list(dict.fromkeys([*p.flags, *injection_flags((f.order or {}).get("note", ""))]))
        return Risk(amount_paise=amount, auto_limit_paise=auto, over_auto_limit=bool(amount and amount > auto),
                    over_hard_cap=bool(amount and amount > cap), refunds_30d=len(f.customer_refunds_30d),
                    guard_score=p.guard_score, flags=flags)

    def _evaluate(self, p: ProposalIn, args: dict, f: Facts) -> list[ClaimResult]:
        present = {c.kind for c in p.claims}
        results = [ClaimResult(kind=k, ok=False, why=f"required claim \"{k.value}\" is missing from the proposal", tier="REQ")
                   for k in sorted(required_for(p.tool, args) - present, key=lambda k: k.value)]
        results += [check(c, f) for c in p.claims]
        return results

    def _summary(self, p: ProposalIn, f: Facts, reasons: list[str]) -> str:
        o = f.order or {}
        who = (f.customer or {}).get("name", p.caller.customer_id)
        what = {WriteTool.issue_refund: f"refund {rupees(f.amount)}", WriteTool.create_return_pickup: "a return pickup",
                WriteTool.update_address: "an address change", WriteTool.cancel_order: "a cancellation"}[p.tool]
        why = {"over_auto_limit": f"above your {rupees(int(f.settings.get('auto_limit_paise', 50000)))} auto-limit",
               "over_hard_cap": "above the hard cap", "refund_frequency": "they had another refund in the last 30 days",
               "guard_flag": "the message looks like pressure or manipulation", "source_unavailable": "the courier system is down",
               "instruction_in_record": "the order note contains a hidden instruction"}
        because = "; ".join(why.get(r, r) for r in reasons)
        return f"{who} asks for {what} on order {o.get('id', p.args.get('order_id'))} ({o.get('item', '?')}). All checks passed. Needs you because: {because}."

    # ───────────────────────── verify ─────────────────────────
    async def verify(self, p: ProposalIn, *, parent_id: str | None = None, cleared: set[str] | None = None) -> VerdictOut:
        t0 = time.perf_counter()
        try:
            args = p.typed_args().model_dump()
        except ValidationError as e:
            raise TrustError(422, f"invalid arguments for {p.tool.value}: {e.errors()[0]['msg']}") from e
        pid = "prp_" + secrets.token_hex(8)
        ah = args_hash(p.tool.value, args)
        f, unavailable = await self._facts(p, args)
        results = self._evaluate(p, args, f) if not unavailable else []
        risk = self._risk(p, f)
        verdict, reasons = decide(p.tool, results, risk, source_unavailable=unavailable)
        if cleared and verdict is Verdict.ESCALATE and set(reasons) <= cleared:
            verdict, reasons = Verdict.ALLOW, []   # a human already accepted exactly these risks

        out = VerdictOut(proposal_id=pid, verdict=verdict, reasons=reasons, results=results, risk=risk)
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """INSERT INTO proposals(id, trace_id, parent_id, tool, args, args_hash, claims, caller, guard_score, flags)
                   VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7::jsonb,$8::jsonb,$9,$10::jsonb)""",
                pid, p.trace_id, parent_id, p.tool.value, args, ah, [c.model_dump(mode="json") for c in p.claims],
                p.caller.model_dump(), p.guard_score, risk.flags)
            await conn.execute("INSERT INTO verdicts(proposal_id, verdict, reasons, results, risk) VALUES ($1,$2,$3::jsonb,$4::jsonb,$5::jsonb)",
                               pid, verdict.value, reasons, [r.model_dump(mode="json") for r in results], risk.model_dump())
            if verdict is Verdict.ESCALATE and parent_id is None:
                out.approval_id = await conn.fetchval("INSERT INTO approvals(proposal_id, summary) VALUES ($1,$2) RETURNING id",
                                                      pid, self._summary(p, f, reasons))
            await self._event(conn, p.trace_id, "verify", {"ALLOW": "ok", "ESCALATE": "warn", "BLOCK": "fail"}[verdict.value], t0,
                              {"proposal_id": pid, "verdict": verdict.value, "reasons": reasons,
                               "claims": [r.model_dump(mode="json") for r in results]})
            await self._audit(conn, "verdict", f"{verdict.value} {p.tool.value} order {args.get('order_id')}" + (f": {', '.join(reasons)}" if reasons else ""),
                              {"proposal_id": pid, "trace_id": p.trace_id, "args": args, "reasons": reasons, "customer": p.caller.customer_id})
        if verdict is Verdict.ALLOW and parent_id is None:
            out.token = tokens.mint(self._secret, pid=pid, tool=p.tool.value, ah=ah, verdict="ALLOW", ttl_s=self.allow_ttl_s)
        return out

    # ───────────────────────── seller decision ─────────────────────────
    async def decide(self, approval_id: int, d: Decision) -> VerdictOut:
        async with self.pool.acquire() as conn, conn.transaction():
            a = await conn.fetchrow("SELECT * FROM approvals WHERE id = $1 FOR UPDATE", approval_id)
            if a is None:
                raise TrustError(404, "approval not found")
            if a["status"] != "pending":
                raise TrustError(409, f"already {a['status']}")
            prop = await conn.fetchrow("SELECT * FROM proposals WHERE id = $1", a["proposal_id"])
            v = await conn.fetchrow("SELECT reasons FROM verdicts WHERE proposal_id = $1", a["proposal_id"])
            features = {"tool": prop["tool"], "amount_paise": prop["args"].get("amount_paise"), "reasons": v["reasons"],
                        "guard_score": prop["guard_score"]}
            if d.decision == "reject":
                await conn.execute("UPDATE approvals SET status='rejected', decided_via=$2, decided_at=now() WHERE id=$1", approval_id, d.decided_via)
                await conn.execute("INSERT INTO seller_precedents(proposal_id, features, decision) VALUES ($1,$2::jsonb,'rejected')", prop["id"], features)
                await self._audit(conn, "approval", f"seller rejected {prop['tool']} (approval {approval_id}) via {d.decided_via}",
                                  {"approval_id": approval_id, "proposal_id": prop["id"]})
                return VerdictOut(proposal_id=prop["id"], verdict=Verdict.BLOCK, reasons=["seller_rejected"], results=[], risk=Risk())

        # approve: re-verify against fresh records (the world may have changed since the card was sent)
        args = dict(prop["args"])
        if d.edited_amount_paise is not None:
            if prop["tool"] != WriteTool.issue_refund.value:
                raise TrustError(422, "only refund amounts can be edited")
            args["amount_paise"] = d.edited_amount_paise
        p = ProposalIn(trace_id=prop["trace_id"], tool=WriteTool(prop["tool"]), args=args,
                       claims=[Claim.model_validate(c) for c in prop["claims"]], caller=prop["caller"],
                       guard_score=prop["guard_score"], flags=prop["flags"])
        re_v = await self.verify(p, parent_id=prop["id"], cleared=HUMAN_CLEARED)
        async with self.pool.acquire() as conn, conn.transaction():
            if re_v.verdict is Verdict.ALLOW:
                await conn.execute("UPDATE approvals SET status='approved', decided_via=$2, decided_at=now(), edited_args=$3::jsonb WHERE id=$1",
                                   approval_id, d.decided_via, args if d.edited_amount_paise is not None else None)
                await conn.execute("INSERT INTO seller_precedents(proposal_id, features, decision) VALUES ($1,$2::jsonb,'approved')",
                                   prop["id"], {**features, "edited": d.edited_amount_paise is not None})
                await self._audit(conn, "approval", f"seller approved {prop['tool']} (approval {approval_id}) via {d.decided_via}",
                                  {"approval_id": approval_id, "proposal_id": re_v.proposal_id, "args": args})
                re_v.token = tokens.mint(self._secret, pid=re_v.proposal_id, tool=prop["tool"], ah=args_hash(prop["tool"], args),
                                         verdict="APPROVED", ttl_s=self.approved_ttl_s)
            elif re_v.verdict is Verdict.BLOCK:
                await conn.execute("UPDATE approvals SET status='void', decided_via=$2, decided_at=now() WHERE id=$1", approval_id, d.decided_via)
                await self._audit(conn, "approval", f"approval {approval_id} void: re-check failed ({', '.join(re_v.reasons)})",
                                  {"approval_id": approval_id, "reasons": re_v.reasons})
            # ESCALATE here means a source is down: the approval stays pending so the seller can retry
        return re_v

    # ───────────────────────── execute ─────────────────────────
    async def execute(self, req: ExecuteIn) -> ExecuteOut:
        t0 = time.perf_counter()
        try:
            tok = tokens.verify(self._secret, req.token)
        except tokens.TokenError as e:
            return await self._log_refusal(req, f"token: {e}", t0)
        try:
            args = ARGS_MODEL[req.tool].model_validate(req.args).model_dump()
        except ValidationError:
            return await self._log_refusal(req, "invalid arguments", t0)
        if tok.pid != req.proposal_id or tok.tool != req.tool.value or tok.ah != args_hash(req.tool.value, args):
            return await self._log_refusal(req, "token does not match this action (args hash mismatch)", t0)

        async with self.pool.acquire() as conn:
            prop = await conn.fetchrow("SELECT args_hash, trace_id, parent_id FROM proposals WHERE id = $1", req.proposal_id)
            if prop is None or prop["args_hash"] != tok.ah:
                return await self._log_refusal(req, "token does not match a recorded proposal", t0)
            if tok.v == "APPROVED":
                root = prop["parent_id"] or req.proposal_id
                status = await conn.fetchval("SELECT status FROM approvals WHERE proposal_id = $1", root)
                if status != "approved":
                    return await self._log_refusal(req, "approval is not in approved state", t0)
            s = {r["key"]: r["value"] for r in await conn.fetch("SELECT key, value FROM settings")}
            if s.get("kill_switch"):
                return await self._log_refusal(req, "kill_switch: the seller has frozen all writes", t0)
            n, total = await conn.fetchrow(
                "SELECT count(*), coalesce(sum(amount_paise),0) FROM executions WHERE ts > now() - interval '1 day' AND result->>'status' = 'done'")
            amount = int(args.get("amount_paise", 0))
            if n >= self.daily_write_cap or total + amount > self.daily_refund_cap_paise:
                return await self._log_refusal(req, "daily cap reached", t0)

            # claim single use: the nonce and the proposal are unique in `executions`
            async with conn.transaction():
                existing = await conn.fetchrow("SELECT nonce, result FROM executions WHERE proposal_id = $1 FOR UPDATE", req.proposal_id)
                if existing and existing["result"].get("status") == "done":
                    return ExecuteOut(proposal_id=req.proposal_id, status="already_executed", result=existing["result"])
                if existing and existing["nonce"] != tok.nonce:
                    return await self._log_refusal(req, "a different token was already used for this proposal", t0)
                if not existing:
                    try:
                        await conn.execute("INSERT INTO executions(proposal_id, nonce, tool, amount_paise, result) VALUES ($1,$2,$3,$4,$5::jsonb)",
                                           req.proposal_id, tok.nonce, req.tool.value, amount, {"status": "pending"})
                    except asyncpg.UniqueViolationError:
                        return await self._log_refusal(req, "token already used", t0)

        try:
            result = await self._write(req.tool, args, idem=req.proposal_id)
            outcome: dict[str, Any] = {"status": "done", "record": {k: v for k, v in result.items() if k in ("id", "status", "address", "replayed")}}
        except StoreRefused as e:
            outcome = {"status": "store_refused", "detail": e.detail}
        except (StoreUnavailable, NotFound) as e:
            outcome = {"status": "store_unavailable", "detail": str(e)[:200]}

        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute("UPDATE executions SET result = $2::jsonb, ts = now() WHERE proposal_id = $1", req.proposal_id, outcome)
            ok = outcome["status"] == "done"
            await self._event(conn, prop["trace_id"], "execute", "ok" if ok else "fail", t0,
                              {"proposal_id": req.proposal_id, "tool": req.tool.value, "args": args, "outcome": outcome})
            what = f"{rupees(amount)} refund" if req.tool is WriteTool.issue_refund else req.tool.value
            await self._audit(conn, "execute" if ok else "execute_failed", f"{what} on order {args.get('order_id')}: {outcome['status']}",
                              {"proposal_id": req.proposal_id, "args": args, "outcome": outcome, "verdict": tok.v})
        if outcome["status"] != "done":
            return ExecuteOut(proposal_id=req.proposal_id, status="refused", reason=outcome["status"], result=outcome)
        return ExecuteOut(proposal_id=req.proposal_id, status="executed", result=outcome)

    async def _write(self, tool: WriteTool, args: dict, idem: str) -> dict:
        match tool:
            case WriteTool.issue_refund:
                return await self.store.create_refund(args["order_id"], args["amount_paise"], idem)
            case WriteTool.create_return_pickup:
                return await self.store.create_return(args["order_id"], args["reason"], idem)
            case WriteTool.update_address:
                return await self.store.update_address(args["order_id"], args["new_address"], idem)
            case WriteTool.cancel_order:
                return await self.store.cancel_order(args["order_id"], idem)

    async def _log_refusal(self, req: ExecuteIn, reason: str, t0: float) -> ExecuteOut:
        async with self.pool.acquire() as conn, conn.transaction():
            trace = await conn.fetchval("SELECT trace_id FROM proposals WHERE id = $1", req.proposal_id) or "unknown"
            await self._event(conn, trace, "execute", "fail", t0, {"proposal_id": req.proposal_id, "refused": reason})
            await self._audit(conn, "execute_refused", f"refused {req.tool.value}: {reason}",
                              {"proposal_id": req.proposal_id, "reason": reason, "args": req.args})
        return ExecuteOut(proposal_id=req.proposal_id, status="refused", reason=reason)

    # ───────────────────────── demo provisioning ─────────────────────────
    async def provision(self, channel: str, channel_id: str, name: str | None) -> dict:
        """Find or create the demo customer behind a chat identity (fresh scenario orders, dated from now)."""
        from kavach.db.seed import provision as _provision

        async with self.pool.acquire() as conn:
            if channel == "whatsapp":
                row = await conn.fetchrow("SELECT id, name FROM customers WHERE phone = $1", channel_id.removeprefix("whatsapp:"))
            elif channel == "telegram" and channel_id.isdigit():
                row = await conn.fetchrow("SELECT id, name FROM customers WHERE tg_id = $1", int(channel_id))
            else:
                row = None
            if row:
                return {"customer_id": row["id"], "name": row["name"], "created": False}
            out = await _provision(conn, channel=channel, channel_id=channel_id, name=name)
            return {**out, "created": True}

    # ───────────────────────── seller settings ─────────────────────────
    async def set_setting(self, name: str, value: bool | int, via: str) -> dict:
        out = await self.store.set_setting(name, value)
        async with self.pool.acquire() as conn:
            await self._audit(conn, "setting", f"{name} set to {value} via {via}", {"name": name, "value": value})
        return out

    async def audit_verify(self) -> int | None:
        return await self.pool.fetchval("SELECT audit_verify('audit_log')")

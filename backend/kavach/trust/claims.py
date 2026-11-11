"""T0/T1 claim checks (ARCH §9.4). Each check is a pure function of freshly re-fetched records (`Facts`).

What the agent *says* it saw is never used as evidence: a claim only names what must be true; the
check decides whether it is true from the records. Customer-sourced claims are evaluated the same way
(the customer's "30 days" is ignored and the real window is used); `authority` claims always fail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from kavach.common.contracts import Caller, Claim, ClaimKind, ClaimResult, Source, WriteTool
from kavach.trust.policy import quote_found
from kavach.trust.rules import DAMAGE_REASONS, EXPECTED_STATE, RELEVANT_CLAUSES


@dataclass
class Facts:
    tool: WriteTool
    args: dict
    caller: Caller
    order: dict | None
    customer: dict | None = None
    shipment: dict | None = None
    order_refunds: list[dict] = field(default_factory=list)
    customer_refunds_30d: list[dict] = field(default_factory=list)
    photos: list[dict] = field(default_factory=list)
    order_returns: list[dict] = field(default_factory=list)
    clauses: dict[int, dict] = field(default_factory=dict)
    settings: dict = field(default_factory=dict)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def amount(self) -> int:
        return int(self.args.get("amount_paise") or 0)


def rupees(paise: int) -> str:
    r = paise / 100
    return f"₹{r:,.0f}" if r == int(r) else f"₹{r:,.2f}"


def _delivered_days(f: Facts) -> int | None:
    at = (f.shipment or {}).get("delivered_at")
    if not at:
        return None
    if isinstance(at, str):
        at = datetime.fromisoformat(at)
    return int((f.now - at).total_seconds() // 86400)


def _res(c: Claim, ok: bool, why: str, tier: str = "T0") -> ClaimResult:
    return ClaimResult(kind=c.kind, ok=ok, why=why, tier=tier, source=c.source)  # type: ignore[arg-type]


def check(c: Claim, f: Facts) -> ClaimResult:
    o = f.order
    oid = f.args.get("order_id")
    if c.kind is ClaimKind.authority:
        return _res(c, False, "authority claimed in a message (\"the owner said…\") cannot replace a record or widen a limit")
    if o is None and c.kind not in (ClaimKind.policy,):
        return _res(c, False, f"order {oid} not found")

    match c.kind:
        case ClaimKind.ownership:
            ok = o["customer_id"] == f.caller.customer_id
            return _res(c, ok, f"order {oid} belongs to the caller" if ok else f"order {oid} belongs to a different customer")

        case ClaimKind.state:
            want = EXPECTED_STATE[f.tool]
            if want == "delivered":
                st = (f.shipment or {}).get("status")
                ok = st == "delivered"
                return _res(c, ok, f"courier says delivered {_delivered_days(f)} day(s) ago" if ok else f"courier status is \"{st or 'none'}\", not delivered")
            ok = o["status"] in ("placed", "packed")
            return _res(c, ok, f"order is \"{o['status']}\": not yet dispatched" if ok else f"order is \"{o['status']}\": already dispatched")

        case ClaimKind.temporal:
            days, window = _delivered_days(f), int(f.settings.get("window_days", 7))
            if days is None:
                return _res(c, False, "no delivery date on record")
            ok = days <= window
            note = " (the customer's claim is ignored; checked against the courier record)" if c.source is Source.customer else ""
            return _res(c, ok, f"{days} day(s) since delivery vs the {window}-day window{note}")

        case ClaimKind.monetary:
            left = o["paid_paise"] - o["refunded_paise"]
            ok = 0 < f.amount <= left
            return _res(c, ok, f"{rupees(f.amount)} requested vs {rupees(left)} refundable (paid {rupees(o['paid_paise'])}, refunded {rupees(o['refunded_paise'])})")

        case ClaimKind.duplicate:
            if f.tool is WriteTool.issue_refund:
                ok = not f.order_refunds and o["refunded_paise"] == 0
                return _res(c, ok, "no earlier refund on this order" if ok else f"an earlier refund of {rupees(o['refunded_paise'])} already exists on this order")
            ok = not f.order_returns
            return _res(c, ok, "no earlier return on this order" if ok else "a return pickup is already booked for this order")

        case ClaimKind.eligibility:
            if o["status"] == "cancelled":
                return _res(c, False, "order was cancelled")
            ok = not o["perishable"]
            return _res(c, ok, "item is returnable" if ok else f"\"{o['item']}\" is perishable and cannot be returned (policy clause 3)")

        case ClaimKind.evidence:
            if f.args.get("reason") not in DAMAGE_REASONS:
                return _res(c, True, "no photo needed for this reason")
            ok = len(f.photos) > 0
            return _res(c, ok, "photo of the item is on file" if ok else "no photo on file; the damage policy needs a clear photo")

        case ClaimKind.frequency:
            n, cap = len(f.customer_refunds_30d), 3
            ok = n < cap
            return _res(c, ok, f"{n} refund(s) for this customer in the last 30 days" + ("" if ok else f" (limit {cap})"))

        case ClaimKind.channel_identity:
            cust = f.customer or {}
            ch = f.caller
            if ch.channel == "whatsapp":
                ok = bool(cust.get("phone")) and ch.channel_user_id.removeprefix("whatsapp:") == cust["phone"]
            elif ch.channel == "telegram":
                ok = str(cust.get("tg_id") or "") == ch.channel_user_id
            else:  # web / test sessions are bound to their demo customer by the gateway
                ok = ch.customer_id == o["customer_id"]
            return _res(c, ok, "message came from the customer's registered number" if ok else "message did not come from the number on the order")

        case ClaimKind.policy:
            if c.source is Source.customer:
                return _res(c, False, "a policy quoted by the customer is not accepted; only the written policy counts", "T1")
            relevant = RELEVANT_CLAUSES[f.tool]
            if c.clause_id is None or not c.quote:
                return _res(c, False, "no clause number or quote supplied", "T1")
            if c.clause_id not in relevant:
                return _res(c, False, f"clause {c.clause_id} does not cover {f.tool.value} (relevant: {sorted(relevant)})", "T1")
            if f.tool is WriteTool.issue_refund and f.args.get("reason") in DAMAGE_REASONS and c.clause_id != 2:
                return _res(c, False, "a damage or wrong-item refund must cite clause 2", "T1")
            clause = f.clauses.get(c.clause_id)
            if clause is None:
                return _res(c, False, f"clause {c.clause_id} does not exist", "T1")
            ok = quote_found(clause["text"], c.quote)
            return _res(c, ok, f"quote found word for word in clause {c.clause_id}" if ok
                        else f"quote not found in clause {c.clause_id}. Quoted: \"{c.quote[:120]}\". Actual: \"{clause['text']}\"", "T1")

    return _res(c, False, f"unknown claim kind {c.kind}")

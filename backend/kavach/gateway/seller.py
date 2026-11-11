"""Seller commands from WhatsApp or Telegram (no app to install, works on any phone).

    1 / approve / haan            approve the newest pending request      (approve 12 → a specific one)
    2 / reject / nahi             reject the newest pending request       (reject 12)
    freeze / unfreeze             kill switch for every write (refunds, returns, address changes)
    status                        pending requests and today's numbers

Only messages that match these commands are treated as seller actions, so the same phone can also chat
as a customer while testing. First decision on any channel wins; the others are told it's already handled.
"""
from __future__ import annotations

import re

from kavach.agent import replies as R

_CMD = re.compile(r"^\s*(?P<verb>1|2|approve|reject|haan|ha|nahi|na|yes|no|freeze|unfreeze|status|pending)\b\s*#?(?P<id>\d+)?\s*$", re.I)
APPROVE = {"1", "approve", "haan", "ha", "yes"}
REJECT = {"2", "reject", "nahi", "na", "no"}


def parse(text: str) -> tuple[str, int | None] | None:
    m = _CMD.match(text or "")
    if not m:
        return None
    verb = m.group("verb").lower()
    kind = "approve" if verb in APPROVE else "reject" if verb in REJECT else verb if verb != "pending" else "status"
    return kind, int(m.group("id")) if m.group("id") else None


async def handle(app, text: str, via: str) -> str | None:
    """Returns the reply for the seller, or None if the text is not a seller command."""
    cmd = parse(text)
    if cmd is None:
        return None
    kind, aid = cmd
    st = app.state
    if kind in ("freeze", "unfreeze"):
        status, out = await st.trust.set_setting("kill_switch", kind == "freeze", st.seller_pin, via)
        if status != 200:
            return f"Couldn't change the kill switch ({out.get('detail', status)})."
        return ("🧊 Frozen: no refunds, returns or changes will run until you send 'unfreeze'. Customers can still ask questions."
                if kind == "freeze" else "✅ Unfrozen: Kavach is acting again within your limits.")
    pending = await st.trust.approvals("pending")
    if kind == "status":
        stats = await st.pool.fetchrow(
            """SELECT count(*) FILTER (WHERE verdict='ALLOW') a, count(*) FILTER (WHERE verdict='BLOCK') b
               FROM verdicts WHERE ts > now() - interval '1 day'""")
        lines = [f"#{p['id']}: {p['summary'][:110]}" for p in pending[:5]]
        return (f"🛡 Kavach today: {stats['a']} handled automatically, {stats['b']} blocked, {len(pending)} waiting for you."
                + ("\n" + "\n".join(lines) + "\nReply 'approve <n>' or 'reject <n>'." if lines else ""))
    if aid is None:
        if not pending:
            return "Nothing is waiting for you right now."
        aid = pending[0]["id"]
    res = await st.agent.decide(aid, {"decision": kind, "decided_via": via, "edited_amount_paise": None})
    if res.get("status") == "not_pending":
        return f"#{aid} was already handled."
    if res.get("status") == "executed":
        args = next((p["args"] for p in pending if p["id"] == aid), {})
        amount = f" {R.rs(args['amount_paise'])}" if args.get("amount_paise") else ""
        await st.out.broadcast_seller(f"✅ #{aid} approved via {via}{amount}; done and the customer has been told.", exclude=via)
        return f"✅ Approved #{aid}{amount}. Done, and the customer has been told."
    if res.get("status") == "rejected":
        await st.out.broadcast_seller(f"❌ #{aid} rejected via {via}.", exclude=via)
        return f"❌ Rejected #{aid}. The customer has been told politely."
    return f"#{aid}: {res.get('status')} ({res.get('reason') or res.get('detail') or ''})".strip()

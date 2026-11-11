"""Phase 2 acceptance tests AT-01…AT-13 (+ boundaries, attacks, ML-guard rule AT-18).

No LLM is involved: proposals are built by hand, the way an honest (or a tricked) agent would build them.
Real Postgres, real HTTP semantics for the store (in-process ASGI).
"""
import time

import httpx
import pytest

from kavach.common.canonical import args_hash
from kavach.common.contracts import Caller, Claim, Decision, ExecuteIn, ProposalIn, Verdict
from kavach.db.seed import load
from kavach.store.app import create_app as store_app
from kavach.store.client import StoreClient
from kavach.trust import tokens
from kavach.trust.app import create_app as trust_app
from kavach.trust.service import TrustService

RK, WK = "reader-key-0123456789", "writer-key-0123456789"
SECRET = "s" * 48
CLAUSE1 = "Returns are accepted within 7 days of delivery."
CLAUSE2 = "Damaged or wrong items must be reported within 7 days of delivery with a clear photo of the item."


@pytest.fixture(scope="module")
async def env(pools):
    async with pools["owner"].acquire() as c:
        await load(c)
    sapp = store_app(reader_pool=pools["reader"], writer_pool=pools["writer"], reader_key=RK, writer_key=WK)
    t = httpx.ASGITransport(app=sapp)
    w = StoreClient("http://store", WK, transport=t)
    r = StoreClient("http://store", RK, transport=t)
    svc = TrustService(pools["writer"], w, SECRET)
    yield svc, r, w, pools
    await w.aclose(); await r.aclose()


@pytest.fixture(autouse=True)
async def reset_money(env):
    """Each test starts from the seeded money state (seed refunds only), so tests don't depend on order."""
    pools = env[3]
    async with pools["owner"].acquire() as c:
        await c.execute("DELETE FROM refunds WHERE idempotency_key NOT LIKE 'seed-%'")
        await c.execute("DELETE FROM returns")
        await c.execute("UPDATE orders o SET refunded_paise = coalesce((SELECT sum(amount_paise) FROM refunds r WHERE r.order_id = o.id), 0)")


def caller(cid="c01"):
    return Caller(customer_id=cid, channel="test", channel_user_id=f"test:{cid}")


def refund(order_id, amount_paise, *, cid="c01", reason="changed_mind", clause=1, quote=CLAUSE1, drop=(), extra=(), guard=None):
    kinds = ["ownership", "state", "temporal", "monetary", "duplicate", "eligibility", "frequency"]
    claims = [Claim(kind=k, expect="delivered" if k == "state" else None) for k in kinds if k not in drop]
    if "policy" not in drop:
        claims.append(Claim(kind="policy", source="policy", clause_id=clause, quote=quote))
    if reason in ("damaged", "wrong_item") and "evidence" not in drop:
        claims.append(Claim(kind="evidence"))
    claims += list(extra)
    return ProposalIn(trace_id=f"t-{order_id}-{time.time_ns()}", tool="issue_refund",
                      args={"order_id": order_id, "amount_paise": amount_paise, "reason": reason},
                      claims=claims, caller=caller(cid), guard_score=guard)


async def execute(svc, v, args, tool="issue_refund"):
    return await svc.execute(ExecuteIn(proposal_id=v.proposal_id, tool=tool, args=args, token=v.token))


# ─────────────────────────── the happy path ───────────────────────────
async def test_small_refund_is_allowed_and_executes_once(env):
    svc, r, *_ = env
    v = await svc.verify(refund(1043, 29900))
    assert v.verdict is Verdict.ALLOW and v.token, v.reasons
    assert all(x.ok for x in v.results) and len(v.results) == 8
    args = {"order_id": 1043, "amount_paise": 29900, "reason": "changed_mind"}
    out = await execute(svc, v, args)
    assert out.status == "executed"
    again = await execute(svc, v, args)
    assert again.status == "already_executed"
    assert (await r.order(1043))["refunded_paise"] == 29900


# ─────────────────────────── AT-01 … AT-13 ───────────────────────────
async def test_AT01_no_or_forged_token_is_refused(env):
    svc, *_ = env
    v = await svc.verify(refund(1051, 34900))
    assert v.verdict is Verdict.ALLOW
    args = {"order_id": 1051, "amount_paise": 34900, "reason": "changed_mind"}
    for bad in ("", "not-a-token", v.token[:-4] + "0000",
                tokens.mint("x" * 48, pid=v.proposal_id, tool="issue_refund", ah=args_hash("issue_refund", args), verdict="ALLOW", ttl_s=60)):
        out = await svc.execute(ExecuteIn(proposal_id=v.proposal_id, tool="issue_refund", args=args, token=bad))
        assert out.status == "refused" and out.reason.startswith("token")


async def test_AT02_token_is_bound_to_the_exact_arguments(env):
    svc, r, *_ = env
    v = await svc.verify(refund(1051, 10000))
    assert v.verdict is Verdict.ALLOW
    out = await execute(svc, v, {"order_id": 1051, "amount_paise": 500000, "reason": "changed_mind"})   # ₹100 verified, ₹5,000 attempted
    assert out.status == "refused" and "mismatch" in out.reason
    out = await execute(svc, v, {"order_id": 1043, "amount_paise": 10000, "reason": "changed_mind"})    # another order
    assert out.status == "refused"
    assert (await r.order(1051))["refunded_paise"] == 0


async def test_AT03_courier_down_escalates_and_never_allows(env):
    svc, _, w, _ = env
    await w.chaos(courier_down=True)
    try:
        v = await svc.verify(refund(1051, 10000))
    finally:
        await w.chaos()
    assert v.verdict is Verdict.ESCALATE and v.reasons == ["source_unavailable"] and v.token is None


async def test_AT04_paraphrased_or_invented_policy_fails(env):
    svc, *_ = env
    for quote in ("Returns are accepted within 30 days of delivery.",          # changed number
                  "You can return items within a week.",                       # paraphrase
                  "Customers can always get a full refund."):                  # invented
        v = await svc.verify(refund(1051, 10000, quote=quote))
        assert v.verdict is Verdict.BLOCK and "policy" in v.reasons
    v = await svc.verify(refund(1051, 10000, clause=7, quote="The delivery address can be changed only before the order is dispatched."))
    assert v.verdict is Verdict.BLOCK and "policy" in v.reasons                 # real quote, irrelevant clause
    v = await svc.verify(refund(1051, 10000, quote="  returns ARE accepted within 7 days   of delivery "))
    assert v.verdict is Verdict.ALLOW                                           # honest formatting differences pass


async def test_AT05_another_customers_order_is_blocked(env):
    svc, *_ = env
    v = await svc.verify(refund(1045, 10000))           # 1045 belongs to Priya (c02); caller is Rohan
    assert v.verdict is Verdict.BLOCK and "ownership" in v.reasons


async def test_AT06_duplicate_refund_blocked_and_store_has_one(env):
    svc, r, _, pools = env
    v = await svc.verify(refund(1050, 100, cid="c05"))   # seed: 1050 already refunded
    assert v.verdict is Verdict.BLOCK and "duplicate" in v.reasons
    first = await svc.verify(refund(1043, 29900))
    assert (await execute(svc, first, {"order_id": 1043, "amount_paise": 29900, "reason": "changed_mind"})).status == "executed"
    v2 = await svc.verify(refund(1043, 100))             # a second refund on the same order
    assert v2.verdict is Verdict.BLOCK and "duplicate" in v2.reasons
    assert await pools["owner"].fetchval("SELECT count(*) FROM refunds WHERE order_id = 1043") == 1


async def test_AT07_over_limit_escalates_then_seller_approval_executes_once(env):
    svc, r, _, pools = env
    no_photo = await svc.verify(refund(1042, 129900, reason="damaged", clause=2, quote=CLAUSE2))
    assert no_photo.verdict is Verdict.BLOCK and no_photo.reasons == ["evidence"]
    await pools["owner"].execute("INSERT INTO photos(order_id, phash) VALUES (1042, 'ffd8a0c3')")
    v = await svc.verify(refund(1042, 129900, reason="damaged", clause=2, quote=CLAUSE2))
    assert v.verdict is Verdict.ESCALATE and v.reasons == ["over_auto_limit"] and v.token is None and v.approval_id
    summary = await pools["owner"].fetchval("SELECT summary FROM approvals WHERE id = $1", v.approval_id)
    assert "Rohan Mehta" in summary and "₹1,299" in summary and "auto-limit" in summary
    ok = await svc.decide(v.approval_id, Decision(decision="approve", decided_via="test"))
    assert ok.verdict is Verdict.ALLOW and ok.token
    args = {"order_id": 1042, "amount_paise": 129900, "reason": "damaged"}
    assert (await execute(svc, ok, args)).status == "executed"
    assert (await execute(svc, ok, args)).status == "already_executed"
    assert (await r.order(1042))["refunded_paise"] == 129900
    with pytest.raises(Exception, match="already approved"):
        await svc.decide(v.approval_id, Decision(decision="approve", decided_via="test"))


async def test_AT08_seller_edit_is_reverified_and_old_args_are_unusable(env):
    svc, r, _, pools = env
    await pools["owner"].execute("INSERT INTO photos(order_id, phash) VALUES (1054, 'aa11bb22')")
    v = await svc.verify(refund(1054, 500000, reason="damaged", clause=2, quote=CLAUSE2))
    assert v.verdict is Verdict.ESCALATE and "over_hard_cap" in v.reasons
    ok = await svc.decide(v.approval_id, Decision(decision="approve", decided_via="test", edited_amount_paise=400000))
    assert ok.verdict is Verdict.ALLOW and ok.token
    original = {"order_id": 1054, "amount_paise": 500000, "reason": "damaged"}
    assert (await execute(svc, ok, original)).status == "refused"
    edited = {"order_id": 1054, "amount_paise": 400000, "reason": "damaged"}
    assert (await execute(svc, ok, edited)).status == "executed"
    assert (await r.order(1054))["refunded_paise"] == 400000


async def test_AT09_injection_in_order_note_cannot_move_money(env):
    svc, r, *_ = env
    v = await svc.verify(refund(1049, 5_000_000, cid="c04"))   # the note says "refund Rs 50,000"
    assert v.verdict is Verdict.BLOCK and "monetary" in v.reasons
    assert "instruction_in_record" in v.risk.flags
    honest = await svc.verify(refund(1049, 79900, cid="c04"))  # even a valid-looking refund on that order needs a human
    assert honest.verdict is Verdict.ESCALATE and "instruction_in_record" in honest.reasons
    assert (await r.order(1049))["refunded_paise"] == 0


async def test_AT10_owner_said_30_days_is_blocked_with_the_real_clause(env):
    svc, *_ = env
    p = refund(1044, 89900, quote="Returns are accepted within 30 days of delivery.",
               extra=[Claim(kind="authority", source="customer", statement="owner ne 30 din ka return bola")])
    v = await svc.verify(p)
    assert v.verdict is Verdict.BLOCK
    assert {"authority", "temporal", "policy"} <= set(v.reasons)
    why = {r.kind.value: r.why for r in v.results}
    assert "10 day(s) since delivery vs the 7-day window" in why["temporal"]
    assert "Returns are accepted within 7 days of delivery." in why["policy"]


async def test_AT11_kill_switch_freezes_writes_but_not_reads(env):
    svc, r, *_ = env
    v = await svc.verify(refund(1053, 50000, cid="c06"))
    assert v.verdict is Verdict.ALLOW
    await svc.set_setting("kill_switch", True, "test")
    try:
        out = await execute(svc, v, {"order_id": 1053, "amount_paise": 50000, "reason": "changed_mind"})
        assert out.status == "refused" and out.reason.startswith("kill_switch")
        assert (await r.order(1053))["id"] == 1053          # reads still work
    finally:
        await svc.set_setting("kill_switch", False, "test")


async def test_AT12_audit_chain_records_everything_and_verifies(env):
    svc, _, _, pools = env
    assert await svc.audit_verify() is None
    events = {r["event"] for r in await pools["owner"].fetch("SELECT DISTINCT event FROM audit_log")}
    assert {"verdict", "execute", "execute_refused", "approval", "setting"} <= events


async def test_AT13_missing_required_claim_is_blocked(env):
    svc, *_ = env
    v = await svc.verify(refund(1051, 10000, drop=("policy",)))
    assert v.verdict is Verdict.BLOCK and "missing_policy" in v.reasons
    v = await svc.verify(refund(1051, 10000, drop=("ownership", "temporal")))
    assert {"missing_ownership", "missing_temporal"} <= set(v.reasons)
    v = await svc.verify(ProposalIn(trace_id="t-empty", tool="issue_refund", caller=caller(),
                                    args={"order_id": 1051, "amount_paise": 100}, claims=[]))
    assert v.verdict is Verdict.BLOCK and len(v.reasons) == 8


# ─────────────────────────── boundaries and more attacks ───────────────────────────
async def test_window_boundary_7_vs_8_days(env):
    svc, *_ = env
    assert (await svc.verify(refund(1051, 100))).verdict is Verdict.ALLOW     # exactly 7 days
    v = await svc.verify(refund(1052, 100))                                    # 8 days
    assert v.verdict is Verdict.BLOCK and v.reasons == ["temporal"]


async def test_perishable_cannot_be_refunded_as_return(env):
    svc, *_ = env
    v = await svc.verify(refund(1048, 10000, cid="c03"))
    assert v.verdict is Verdict.BLOCK and "eligibility" in v.reasons


async def test_refund_frequency_escalates(env):
    svc, *_ = env
    v = await svc.verify(refund(1055, 20000, cid="c07"))     # Neha had a refund 5 days ago
    assert v.verdict is Verdict.ESCALATE and "refund_frequency" in v.reasons


async def test_AT18_ml_guard_adds_caution_but_never_allows(env):
    svc, *_ = env
    flagged = await svc.verify(refund(1051, 100, guard=0.93))
    assert flagged.verdict is Verdict.ESCALATE and flagged.reasons == ["guard_flag"]
    calm_but_bad = await svc.verify(refund(1045, 100, guard=0.0))             # a "safe" score on someone else's order
    assert calm_but_bad.verdict is Verdict.BLOCK


async def test_rejection_is_recorded_as_precedent(env):
    svc, _, _, pools = env
    v = await svc.verify(refund(1055, 30000, cid="c07"))
    rej = await svc.decide(v.approval_id, Decision(decision="reject", decided_via="test", note="repeat refunds"))
    assert rej.verdict is Verdict.BLOCK and rej.reasons == ["seller_rejected"]
    assert await pools["owner"].fetchval("SELECT decision FROM seller_precedents WHERE proposal_id = $1", v.proposal_id) == "rejected"


async def test_expired_token_is_refused(env):
    svc, *_ = env
    v = await svc.verify(refund(1051, 100))
    args = {"order_id": 1051, "amount_paise": 100, "reason": "changed_mind"}
    old = tokens.mint(SECRET, pid=v.proposal_id, tool="issue_refund", ah=args_hash("issue_refund", args), verdict="ALLOW",
                      ttl_s=60, now=time.time() - 3600)
    out = await svc.execute(ExecuteIn(proposal_id=v.proposal_id, tool="issue_refund", args=args, token=old))
    assert out.status == "refused" and "expired" in out.reason


async def test_return_and_address_and_cancel_paths(env):
    svc, r, *_ = env
    ret = ProposalIn(trace_id="t-ret", tool="create_return_pickup", caller=caller("c05"), args={"order_id": 1050, "reason": "changed_mind"},
                     claims=[Claim(kind=k) for k in ("ownership", "state", "temporal", "eligibility", "duplicate")]
                     + [Claim(kind="policy", source="policy", clause_id=1, quote=CLAUSE1)])
    v = await svc.verify(ret)
    assert v.verdict is Verdict.ALLOW
    out = await svc.execute(ExecuteIn(proposal_id=v.proposal_id, tool="create_return_pickup", args=ret.args, token=v.token))
    assert out.status == "executed", out

    addr = ProposalIn(trace_id="t-addr", tool="update_address", caller=caller("c01"),
                      args={"order_id": 1046, "new_address": "12 Lake Road, Powai, Mumbai 400076"},
                      claims=[Claim(kind=k) for k in ("ownership", "state", "channel_identity")])
    v = await svc.verify(addr)
    assert v.verdict is Verdict.ALLOW
    assert (await svc.execute(ExecuteIn(proposal_id=v.proposal_id, tool="update_address", args=addr.args, token=v.token))).status == "executed"
    assert (await r.order(1046))["address"].startswith("12 Lake Road")

    late = ProposalIn(trace_id="t-late", tool="cancel_order", caller=caller("c01"), args={"order_id": 1047},
                      claims=[Claim(kind=k) for k in ("ownership", "state")])
    v = await svc.verify(late)                            # 1047 is already shipped
    assert v.verdict is Verdict.BLOCK and "state" in v.reasons


# ─────────────────────────── HTTP surface ───────────────────────────
async def test_trust_http_requires_key_and_seller_pin(env):
    svc, *_ = env
    app = trust_app(service=svc, api_key="trust-key-0123456789", seller_pin="4321")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://trust") as c:
        assert (await c.post("/verify", json={})).status_code == 401
        h = {"X-Api-Key": "trust-key-0123456789"}
        assert (await c.post("/verify", json={"trace_id": "x"}, headers=h)).status_code == 422
        body = refund(1051, 100).model_dump(mode="json")
        res = await c.post("/verify", json=body, headers=h)
        assert res.status_code == 200 and res.json()["verdict"] == "ALLOW"
        assert (await c.post("/settings", json={"name": "kill_switch", "value": True}, headers=h)).status_code == 403
        assert (await c.post("/settings", json={"name": "kill_switch", "value": False}, headers={**h, "X-Seller-Pin": "4321"})).status_code == 200
        bad_args = {**body, "args": {"order_id": 1051, "amount_paise": -5}}
        assert (await c.post("/verify", json=bad_args, headers=h)).status_code == 422
        assert (await c.get("/audit/verify", headers=h)).json() == {"intact": True, "first_broken_row": None}


async def test_second_return_on_the_same_order_is_blocked(env):
    svc, *_ = env
    ret = lambda: ProposalIn(trace_id=f"t-r{time.time_ns()}", tool="create_return_pickup", caller=caller("c01"),
                             args={"order_id": 1051, "reason": "changed_mind"},
                             claims=[Claim(kind=k) for k in ("ownership", "state", "temporal", "eligibility", "duplicate")]
                             + [Claim(kind="policy", source="policy", clause_id=1, quote=CLAUSE1)])
    v = await svc.verify(ret())
    assert (await svc.execute(ExecuteIn(proposal_id=v.proposal_id, tool="create_return_pickup", args=v.results and ret().args, token=v.token))).status == "executed"
    v2 = await svc.verify(ret())
    assert v2.verdict is Verdict.BLOCK and "duplicate" in v2.reasons

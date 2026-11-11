"""Seller alert calls (D-21). A fake phone service records what would be dialled: no real call is ever placed."""
from __future__ import annotations

import time

import httpx
import pytest
from fastapi import FastAPI
from twilio.request_validator import RequestValidator

from kavach.events import EventBus
from kavach.gateway import calls as calls_mod
from kavach.gateway.calls import SellerCalls

ENV = {"CALLS_ENABLED": "1", "CALL_DRY_RUN": "0", "TWILIO_ACCOUNT_SID": "AC" + "0" * 32, "TWILIO_AUTH_TOKEN": "tok-123",
       "TWILIO_CALLER_ID": "+15550000001", "CALL_TO": "+919800000110", "CALL_DAILY_CAP": "3", "CALL_TOTAL_CAP": "10",
       "CALL_COOLDOWN_MIN": "30", "CALL_APPROVAL_WAIT_S": "0"}
REAL = {"channel": "whatsapp", "user_id": "+919811111111", "customer_id": "c01", "name": "Priya"}
TEST = {"channel": "web", "user_id": "verify_0123456789abcdef", "customer_id": "c02"}


class FakePhone:
    def __init__(self):
        self.calls: list[dict] = []

    async def __call__(self, method, url, data):
        self.calls.append({"method": method, "url": url, **(data or {})})
        return {"sid": "CA" + "f" * 32, "status": "queued"}


@pytest.fixture
async def phone(pools):
    async with pools["owner"].acquire() as c:
        await c.execute("DELETE FROM usage_counters WHERE key LIKE 'calls:%'")
    return FakePhone()


def make(pools, phone, **over):
    env = {**ENV, **over}
    decided = []

    async def decide(aid, d):
        decided.append((aid, d))
        return {"status": "executed" if d["decision"] == "approve" else "rejected"}

    async def pending(aid):
        return True
    c = SellerCalls(pools["reader"], EventBus(None), public_base_url="https://api.example", transport=phone, env=env,
                    decide=decide, still_pending=pending)
    return c, decided


async def test_off_unless_configured(pools, phone):
    c, _ = make(pools, phone, CALLS_ENABLED="0")
    assert (await c.place("injection", "hello", None))["action"] == "off" and phone.calls == []


async def test_test_mode_builds_the_call_but_dials_nothing(pools, phone):
    c, _ = make(pools, phone, CALL_DRY_RUN="1")
    r = await c.place("injection", "Hello, this is Kavach.", "tr_x")
    assert r["action"] == "dry_run" and "Kavach" in r["script"] and phone.calls == []


async def test_real_call_goes_only_to_the_configured_number_with_a_time_limit(pools, phone):
    c, _ = make(pools, phone)
    await c.on_card({"kind": "injection", "conv": {**REAL, "user_id": "+910000000000"}, "trace_id": "tr_a"})
    assert len(phone.calls) == 1
    call = phone.calls[0]
    assert call["To"] == ENV["CALL_TO"] and call["From"] == ENV["TWILIO_CALLER_ID"] and call["TimeLimit"] == "35"
    assert "<Say" in call["Twiml"] and "hidden" in call["Twiml"]
    v = await c.view()
    assert v["calls_total"] == 1 and v["to"].endswith("0110") and "+919800000110" not in str(v)


async def test_cooldown_holds_then_mentions_held_alerts(pools, phone):
    c, _ = make(pools, phone)
    assert (await c.place("injection", "first.", None))["action"] == "called"
    assert (await c.place("injection", "second.", None))["action"] == "held"
    assert len(phone.calls) == 1
    await c._set("calls:last_at", int(time.time()) - 31 * 60)          # cooldown over
    r = await c.place("injection", "third.", None)
    assert r["action"] == "called" and "1 more alert" in r["script"]


async def test_daily_and_total_caps(pools, phone):
    c, _ = make(pools, phone, CALL_COOLDOWN_MIN="0", CALL_DAILY_CAP="2")
    assert [(await c.place("x", "a.", None))["action"] for _ in range(3)] == ["called", "called", "cap"]
    c2, _ = make(pools, phone, CALL_COOLDOWN_MIN="0", CALL_DAILY_CAP="9", CALL_TOTAL_CAP="2")
    assert (await c2.place("x", "a.", None))["action"] == "cap"


async def test_our_own_test_sessions_never_ring(pools, phone):
    c, _ = make(pools, phone)
    await c.on_card({"kind": "injection", "conv": TEST, "trace_id": "tr_t"})
    for _ in range(5):
        await c.on_block(TEST, "tr_t", 1)
    assert phone.calls == []


async def test_burst_of_blocks_rings_once(pools, phone):
    c, _ = make(pools, phone)
    for i in range(5):
        await c.on_block(REAL, f"tr_{i}", 200277)
    assert len(phone.calls) == 1 and "3 refund or return requests" in phone.calls[0]["Twiml"] and "200277" in phone.calls[0]["Twiml"]


async def test_big_refund_waiting_asks_for_a_key_press(pools, phone):
    c, decided = make(pools, phone)
    await c.on_card({"kind": "approval", "approval_id": 42, "conv": REAL, "trace_id": "tr_b", "tool": "issue_refund",
                     "args": {"order_id": 200277, "amount_paise": 500000}, "order": {"id": 200277, "item": "Headphones"}, "reasons": ["over_hard_cap"]})
    for t in list(c._tasks):
        await t
    tw = phone.calls[0]["Twiml"]
    assert "<Gather" in tw and "Press 1 to approve" in tw and "5,000 rupees" in tw
    assert f"aid=42&amp;t={c.token_for(42)}" in tw                          # valid XML, our token in the action URL
    small = {"kind": "approval", "approval_id": 43, "conv": REAL, "args": {"amount_paise": 79900}, "order": {"id": 1}}
    await c.on_card(small)
    assert not c._tasks or all(t.done() for t in c._tasks)                   # under the limit: no call scheduled


async def test_key_press_needs_our_token_and_decides_via_phone(pools, phone):
    c, decided = make(pools, phone)
    assert "could not be verified" in await c.on_key(42, "wrong", "1")
    assert "Approved" in await c.on_key(42, c.token_for(42), "1")
    assert decided == [(42, {"decision": "approve", "decided_via": "phone"})]
    assert "No decision" in await c.on_key(42, c.token_for(42), "9")


async def test_voice_webhook_checks_twilio_signature(pools, phone):
    c, decided = make(pools, phone)
    app = FastAPI()
    app.include_router(calls_mod.router)
    app.state.calls = c
    q = f"aid=7&t={c.token_for(7)}"
    form = {"Digits": "2", "CallSid": "CA1"}
    good = RequestValidator(ENV["TWILIO_AUTH_TOKEN"]).compute_signature(f"https://api.example/webhooks/twilio/voice?{q}", form)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as h:
        bad = await h.post(f"/webhooks/twilio/voice?{q}", data=form, headers={"X-Twilio-Signature": "nope"})
        ok = await h.post(f"/webhooks/twilio/voice?{q}", data=form, headers={"X-Twilio-Signature": good})
    assert bad.status_code == 403 and ok.status_code == 200 and "Rejected" in ok.text
    assert decided == [(7, {"decision": "reject", "decided_via": "phone"})]


async def test_script_is_capped_to_about_35_seconds(pools, phone):
    c, _ = make(pools, phone, CALL_DRY_RUN="1")
    r = await c.place("x", "word " * 300, None)
    assert len(r["script"].split()) <= 90


async def test_call_now_records_the_call_and_audio_is_only_for_our_calls(pools, phone):
    c, _ = make(pools, phone)
    r = await c.call_now({"id": 9, "tool": "issue_refund", "args": {"order_id": 1, "amount_paise": 500000}, "trace_id": "tr_now"},
                         {"id": 1, "item": "Headphones"})
    assert r["action"] == "called"
    sent = phone.calls[-1]
    assert sent["Record"] == "true" and "<Gather" in sent["Twiml"] and "5,000 rupees" in sent["Twiml"]
    assert await c.audio("not-a-sid") is None
    assert await c.audio("CA" + "0" * 32) is None                 # well-formed, but Kavach never placed it

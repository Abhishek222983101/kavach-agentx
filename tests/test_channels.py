"""Phase 4 acceptance: WhatsApp (Twilio), Telegram, seller commands, email copies, caps.
Fake Twilio/Telegram/SMTP record what would be sent; nothing leaves this machine."""
import asyncio
import json
from urllib.parse import parse_qs

import httpx
import pytest
from twilio.request_validator import RequestValidator

from kavach import llm
from kavach.gateway.telegram import TelegramBot
from kavach.gateway.whatsapp import TwilioWhatsApp
from tests.test_agent import PIN, FakeLLM, U, world  # noqa: F401  (re-use the agent test world)

SID, TOKEN, SANDBOX = "AC" + "0" * 32, "test-auth-token", "whatsapp:+14155238886"
SELLER = "+919800000001"
BASE = "https://kavach.test"


class Recorder:
    def __init__(self):
        self.wa: list[dict] = []
        self.tg: list[dict] = []
        self.mail: list[tuple[str, str]] = []

    def twilio(self, request: httpx.Request) -> httpx.Response:
        self.wa.append({k: v[0] for k, v in parse_qs(request.content.decode()).items()})
        return httpx.Response(201, json={"sid": "SM" + "1" * 32})

    def telegram(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content or b"{}")
        self.tg.append({"method": request.url.path.rsplit("/", 1)[-1], **body})
        return httpx.Response(200, json={"ok": True, "result": True})


@pytest.fixture
def fake(monkeypatch):
    f = FakeLLM()
    monkeypatch.setattr(llm, "complete_json", f)
    return f


@pytest.fixture
async def chan(world, monkeypatch):  # noqa: F811
    rec = Recorder()
    app = world()

    async def inject(app):
        st = app.state
        st.public_base_url, st.seller_whatsapp, st.seller_telegram, st.telegram_secret = BASE, SELLER, "777", "tg-secret-123"
        st.whatsapp = TwilioWhatsApp(SID, TOKEN, SANDBOX, st.caps, transport=httpx.MockTransport(rec.twilio), min_gap_s=0)
        st.telegram = TelegramBot("123:abc", transport=httpx.MockTransport(rec.telegram))
        st.out.channels.update({"whatsapp": st.whatsapp.send, "telegram": st.telegram.send})
        st.out.seller_targets[:] = [("whatsapp", SELLER), ("telegram", "777")]

        class FakeMailer:
            async def send(self, subject, body):
                rec.mail.append((subject, body))
                return True
        st.out.mailer = FakeMailer()

    app.state.startup_hooks.append(inject)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as c:
            yield c, app, rec


def signed(form: dict) -> dict:
    sig = RequestValidator(TOKEN).compute_signature(f"{BASE}/webhooks/twilio/whatsapp", form)
    return {"X-Twilio-Signature": sig}


async def wa(c, app, frm, body, sid, media=None):
    form = {"From": f"whatsapp:{frm}", "To": SANDBOX, "Body": body, "MessageSid": sid, "NumMedia": "0", "ProfileName": "Asha"}
    if media:
        form.update({"NumMedia": "1", "MediaContentType0": "image/jpeg", "MediaUrl0": "https://api.twilio.com/media/ME1"})
    r = await c.post("/webhooks/twilio/whatsapp", data=form, headers=signed(form))
    assert r.status_code == 200 and "<Response>" in r.text
    await asyncio.gather(*list(app.state.bg_tasks), return_exceptions=True)
    return r


def to(rec, number):
    return [m["Body"] for m in rec.wa if m["To"] == f"whatsapp:{number}"]


# ─────────────────────────────── WhatsApp ───────────────────────────────
async def test_forged_webhook_is_rejected(chan):
    c, _, rec = chan
    form = {"From": "whatsapp:+919811111111", "Body": "refund", "MessageSid": "SMforged"}
    r = await c.post("/webhooks/twilio/whatsapp", data=form, headers={"X-Twilio-Signature": "forged"})
    assert r.status_code == 403 and rec.wa == []


async def test_customer_chats_on_whatsapp_and_gets_a_reply(chan, fake):
    c, app, rec = chan
    cust = "+919811111111"
    await wa(c, app, cust, "namaste", "SM" + "a" * 32)
    assert "Kavach" in to(rec, cust)[-1]
    orders = await app.state.store.orders(
        (await app.state.pool.fetchval("SELECT customer_id FROM conversations WHERE channel='whatsapp' AND user_id=$1", cust)))
    cover = next(o for o in orders if o["item"] == "Phone cover")
    fake.next = U("refund", order_id=cover["id"], reason="changed_mind")
    await wa(c, app, cust, "cover ka refund chahiye", "SM" + "b" * 32)
    assert "return pickup" in to(rec, cust)[-1] and "Ho gaya" in to(rec, cust)[-1]


async def test_duplicate_delivery_is_handled_once(chan, fake):
    c, app, rec = chan
    cust = "+919822222222"
    await wa(c, app, cust, "namaste", "SM" + "c" * 32)
    await wa(c, app, cust, "namaste", "SM" + "c" * 32)        # Twilio retried the same message
    assert len(to(rec, cust)) == 1


async def test_seller_approves_on_whatsapp_with_one_reply(chan, fake):
    c, app, rec = chan
    cust = "+919833333333"
    await wa(c, app, cust, "hi", "SM" + "d" * 32)
    cid = await app.state.pool.fetchval("SELECT customer_id FROM conversations WHERE channel='whatsapp' AND user_id=$1", cust)
    spk = next(o for o in await app.state.store.orders(cid) if o["item"] == "Bluetooth speaker")
    fake.next = U("refund", order_id=spk["id"], reason="damaged")
    await wa(c, app, cust, "speaker toota hai", "SM" + "e" * 32)
    assert "photo" in to(rec, cust)[-1].lower()
    await wa(c, app, cust, "", "SM" + "f" * 32, media=True)          # sends the photo
    assert "seller" in to(rec, cust)[-1]
    card = to(rec, SELLER)[-1]
    assert "Approval needed · #" in card and "₹1,299" in card and "Reply *1*" in card and "auto-refund limit" in card
    tg_card = [m for m in rec.tg if m["method"] == "sendMessage" and m["chat_id"] == "777"][-1]
    assert tg_card["reply_markup"]["inline_keyboard"][0][0]["text"] == "Approve"
    assert rec.mail and "Approval needed · #" in rec.mail[-1][0] and "*" not in rec.mail[-1][0]
    await wa(c, app, SELLER, "1", "SM" + "g" * 32)                   # seller replies "1"
    assert to(rec, SELLER)[-1].startswith("✅ Approved")
    assert "approve kar diya" in to(rec, cust)[-1]
    assert any("already" in m.get("text", "") or "approved via whatsapp" in m.get("text", "") for m in rec.tg)
    await wa(c, app, SELLER, "1", "SM" + "h" * 32)
    assert "Nothing is waiting" in to(rec, SELLER)[-1] or "already" in to(rec, SELLER)[-1]


async def test_seller_freeze_and_status_from_whatsapp(chan, fake):
    c, app, rec = chan
    await wa(c, app, SELLER, "freeze", "SM" + "i" * 32)
    assert "Frozen" in to(rec, SELLER)[-1]
    await wa(c, app, SELLER, "status", "SM" + "j" * 32)
    assert "Kavach today" in to(rec, SELLER)[-1]
    await wa(c, app, SELLER, "unfreeze", "SM" + "k" * 32)
    assert "Unfrozen" in to(rec, SELLER)[-1]


async def test_seller_number_can_still_chat_as_a_customer(chan, fake):
    c, app, rec = chan
    await wa(c, app, SELLER, "namaste", "SM" + "l" * 32)               # not a command -> customer flow
    assert "Kavach" in to(rec, SELLER)[-1]


async def test_whatsapp_daily_cap_stops_sending(chan, fake, monkeypatch):
    c, app, rec = chan
    monkeypatch.setattr(app.state.caps, "whatsapp_out", app.state.caps._wa_out)
    await wa(c, app, "+919844444444", "namaste", "SM" + "m" * 32)
    assert to(rec, "+919844444444") == []


# ─────────────────────────────── Telegram ───────────────────────────────
async def test_telegram_needs_secret_and_handles_customer_and_seller_buttons(chan, fake):
    c, app, rec = chan
    upd = {"update_id": 1, "message": {"chat": {"id": 555}, "from": {"first_name": "Ravi"}, "text": "/start"}}
    assert (await c.post("/webhooks/telegram", json=upd)).status_code == 403
    h = {"X-Telegram-Bot-Api-Secret-Token": "tg-secret-123"}
    assert (await c.post("/webhooks/telegram", json=upd, headers=h)).status_code == 200
    await asyncio.gather(*list(app.state.bg_tasks), return_exceptions=True)
    assert "Kavach" in [m for m in rec.tg if m.get("chat_id") == "555"][-1]["text"]
    cid = await app.state.pool.fetchval("SELECT customer_id FROM conversations WHERE channel='telegram' AND user_id='555'")
    hp = next(o for o in await app.state.store.orders(cid) if o["item"] == "Noise-cancelling headphones")
    fake.next = U("refund", order_id=hp["id"], reason="damaged")
    await c.post("/webhooks/telegram", json={"update_id": 2, "message": {"chat": {"id": 555}, "text": "headphones toote hain"}}, headers=h)
    await asyncio.gather(*list(app.state.bg_tasks), return_exceptions=True)
    photo = {"update_id": 21, "message": {"chat": {"id": 555}, "photo": [{"file_unique_id": "AQADtest"}]}}
    await c.post("/webhooks/telegram", json=photo, headers=h)
    await asyncio.gather(*list(app.state.bg_tasks), return_exceptions=True)
    aid = (await app.state.trust.approvals("pending"))[0]["id"]
    cb = {"update_id": 3, "callback_query": {"id": "cb1", "data": f"reject:{aid}", "message": {"chat": {"id": 777}}}}
    await c.post("/webhooks/telegram", json=cb, headers=h)
    await asyncio.gather(*list(app.state.bg_tasks), return_exceptions=True)
    assert any("Rejected" in m.get("text", "") for m in rec.tg if m.get("chat_id") == "777")
    assert "approve nahi kar paye" in [m for m in rec.tg if m.get("chat_id") == "555"][-1]["text"]
    bad = {"update_id": 4, "callback_query": {"id": "cb2", "data": f"approve:{aid}", "message": {"chat": {"id": 999}}}}
    await c.post("/webhooks/telegram", json=bad, headers=h)                    # not the seller: ignored
    await asyncio.gather(*list(app.state.bg_tasks), return_exceptions=True)
    assert not any(m.get("chat_id") == "999" for m in rec.tg if m["method"] == "sendMessage")


async def test_telegram_orders_and_help_commands(chan, fake):
    c, app, rec = chan
    h = {"X-Telegram-Bot-Api-Secret-Token": "tg-secret-123"}
    for i, cmd in enumerate(("/orders", "/help"), start=10):
        await c.post("/webhooks/telegram", json={"update_id": i, "message": {"chat": {"id": 556}, "text": cmd}}, headers=h)
        await asyncio.gather(*list(app.state.bg_tasks), return_exceptions=True)
    sent = [m["text"] for m in rec.tg if m.get("chat_id") == "556"]
    assert "Your demo orders" in sent[0] and "Bluetooth speaker" in sent[0]
    assert "/orders" in sent[1]


async def test_whatsapp_budget_is_persistent_and_hard(chan, fake):
    from kavach.gateway.budget import WhatsAppBudget
    c, app, rec = chan
    budget = WhatsAppBudget(app.state.pool, limit=(await WhatsAppBudget(app.state.pool).used()) + 3)
    app.state.whatsapp.budget = budget
    cust = "+919855555555"
    await wa(c, app, cust, "namaste", "SM" + "n" * 32)      # inbound counts 1, reply counts 1
    assert len(to(rec, cust)) == 1
    await wa(c, app, cust, "namaste", "SM" + "o" * 32)      # inbound counts 1 -> budget reached, no reply
    assert len(to(rec, cust)) == 1
    assert not await budget.allow()
    fresh = WhatsAppBudget(app.state.pool, limit=budget.limit)  # a "restart" sees the same count
    assert await fresh.used() == await budget.used()


async def test_whatsapp_replies_show_messages_left(chan, fake):
    from kavach.gateway.budget import WhatsAppBudget
    c, app, rec = chan
    app.state.whatsapp.budget = WhatsAppBudget(app.state.pool, limit=(await WhatsAppBudget(app.state.pool).used()) + 50)
    cust = "+919866666666"
    await wa(c, app, cust, "namaste", "SM" + "p" * 32)
    body = to(rec, cust)[-1]
    assert "WhatsApp msgs left" in body and body.rstrip().endswith("_") and "Kavach" in body


async def test_delivery_receipts_are_not_customers():
    """Regression (12 Nov): Twilio status callbacks (From = our sandbox number) were answered like customer messages."""
    from types import SimpleNamespace
    from kavach.gateway import whatsapp as wa
    called = []

    async def handle(*a, **k):
        called.append(a)
    app = SimpleNamespace(state=SimpleNamespace(whatsapp=SimpleNamespace(sender="whatsapp:+14155238886"), agent=SimpleNamespace(handle=handle)))
    for form in ({"From": "whatsapp:+14155238886", "MessageSid": "SM1", "Body": "hi"},
                 {"From": "whatsapp:+919800000000", "MessageSid": "SM2", "MessageStatus": "delivered"},
                 {"From": "whatsapp:+919800000000", "MessageSid": "SM3", "SmsStatus": "read"}):
        await wa._process_inbound(app, form)
    assert called == []

"""Turns channels on from the environment at API startup. Each channel is optional and independent.

WhatsApp:  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, WHATSAPP_MODE=webhook|poll|off
           SELLER_WHATSAPP (the seller's own number, receives approval cards and can send commands)
Telegram:  TELEGRAM_ENABLED=1, TELEGRAM_BOT_TOKEN, TELEGRAM_MODE=webhook|poll, TELEGRAM_WEBHOOK_SECRET,
           SELLER_TELEGRAM_CHAT_ID
Email:     EMAIL_ENABLED=1, SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SELLER_EMAIL (default SMTP_USER)
"""
from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger("kavach.channels")


async def setup(app) -> None:
    st = app.state
    st.public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    st.seller_whatsapp = os.getenv("SELLER_WHATSAPP", "").strip()
    st.seller_telegram = os.getenv("SELLER_TELEGRAM_CHAT_ID", "").split(",")[0].strip()
    st.telegram_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    st.whatsapp = st.telegram = st.mailer = None
    started: list[str] = []

    sid, token, sender = (os.getenv(k, "") for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"))
    mode = os.getenv("WHATSAPP_MODE", "webhook").lower()
    if sid and token and sender and mode != "off":
        from kavach.gateway.whatsapp import TwilioWhatsApp, poll_loop

        st.whatsapp = TwilioWhatsApp(sid, token, sender, st.caps)
        st.out.channels["whatsapp"] = st.whatsapp.send
        if st.seller_whatsapp:
            st.out.seller_targets.append(("whatsapp", st.seller_whatsapp))
        if mode == "poll":
            st.bg_tasks.add(asyncio.create_task(poll_loop(app)))
        started.append(f"whatsapp:{mode}")

    if os.getenv("TELEGRAM_ENABLED", "0") == "1" and (tg_token := os.getenv("TELEGRAM_BOT_TOKEN", "")):
        from kavach.gateway.telegram import TelegramBot, poll_loop as tg_poll

        st.telegram = TelegramBot(tg_token)
        st.out.channels["telegram"] = st.telegram.send
        if st.seller_telegram:
            st.out.seller_targets.append(("telegram", st.seller_telegram))
        if os.getenv("TELEGRAM_MODE", "webhook").lower() == "poll":
            st.bg_tasks.add(asyncio.create_task(tg_poll(app)))
        started.append(f"telegram:{os.getenv('TELEGRAM_MODE', 'webhook')}")

    if os.getenv("EMAIL_ENABLED", "0") == "1" and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"):
        from kavach.gateway.email import Mailer

        st.mailer = Mailer(os.getenv("SMTP_HOST", "smtp.gmail.com"), os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"],
                           os.getenv("SELLER_EMAIL", os.environ["SMTP_USER"]))
        st.out.mailer = st.mailer
        started.append("email")
    log.info("channels: %s", ", ".join(started) or "web only")
    st.channels_started = started


async def teardown(app) -> None:
    for t in list(app.state.bg_tasks):
        t.cancel()
    for c in (app.state.whatsapp, app.state.telegram):
        if c is not None:
            await c.aclose()

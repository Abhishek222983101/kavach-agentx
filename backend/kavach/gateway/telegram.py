"""Telegram bot: customers chat, the seller approves with tap buttons (ARCH §9.1).

Webhook mode (production) checks Telegram's secret-token header; polling mode is for local development.
Disabled unless TELEGRAM_ENABLED=1, so an existing bot's token is never used by accident.
"""
from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request

from kavach.common.canonical import constant_time_equal
from kavach.gateway import seller
from kavach.gateway.identity import TooManyNewCustomers, record_message, resolve

log = logging.getLogger("kavach.telegram")


class TelegramBot:
    def __init__(self, token: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self._c = httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{token}", timeout=35, transport=transport)

    async def aclose(self) -> None:
        await self._c.aclose()

    async def call(self, method: str, **params) -> dict:
        r = await self._c.post(f"/{method}", json=params)
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"telegram {method}: {data.get('description', r.status_code)}")
        return data["result"]

    async def send(self, chat_id: str, text: str, buttons: list[tuple[str, str]] | None = None) -> None:
        params: dict = {"chat_id": chat_id, "text": text[:4000]}
        if buttons:
            params["reply_markup"] = {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in buttons]]}
        await self.call("sendMessage", **params)


async def process_update(app, upd: dict) -> None:
    st = app.state
    if cq := upd.get("callback_query"):                       # seller tapped Approve / Reject
        chat_id = str(cq.get("message", {}).get("chat", {}).get("id", ""))
        try:
            await st.telegram.call("answerCallbackQuery", callback_query_id=cq["id"])
        except Exception:  # noqa: BLE001
            pass
        if chat_id != st.seller_telegram:
            return
        verb, _, aid = (cq.get("data") or "").partition(":")
        if verb in ("approve", "reject") and aid.isdigit():
            reply = await seller.handle(app, f"{verb} {aid}", "telegram")
            if reply:
                await st.telegram.send(chat_id, reply)
        return
    msg = upd.get("message") or {}
    chat_id, text = str(msg.get("chat", {}).get("id", "")), (msg.get("text") or msg.get("caption") or "").strip()[:1000]
    if not chat_id:
        return
    if chat_id == st.seller_telegram and (reply := await seller.handle(app, text, "telegram")) is not None:
        await st.telegram.send(chat_id, reply)
        return
    name = " ".join(filter(None, [msg.get("from", {}).get("first_name"), msg.get("from", {}).get("last_name")])) or None
    try:
        conv = await resolve(st.pool, st.trust, "telegram", chat_id, name, allow_new=st.caps.allow_new_customer)
    except TooManyNewCustomers:
        return
    media = [{"kind": "image", "content_type": "image/jpeg", "sha256": msg["photo"][-1]["file_unique_id"]}] if msg.get("photo") else []
    if msg.get("voice"):
        await st.telegram.send(chat_id, "Voice notes coming soon. Please type your message for now 🙏")
        return
    if not await record_message(st.pool, conv, "in", text or "[photo]", provider_msg_id=f"tg:{upd.get('update_id')}", media=media or None):
        return
    if not st.caps.allow_user(f"telegram:{chat_id}"):
        await st.telegram.send(chat_id, "You've reached today's message limit for this demo. Please try again tomorrow.")
        return
    if text.split("@")[0] == "/orders":
        orders = await st.store.orders(conv["customer_id"], limit=10)
        lines = [f"• {o['item']}: order {o['id']} ({o['status']})" for o in orders]
        await st.telegram.send(chat_id, "Your demo orders:\n" + "\n".join(lines) +
                               "\n\nTry: \"where is my earphone?\", \"phone cover ka refund chahiye\", \"speaker toota hua aaya\".")
        return
    if text.split("@")[0] == "/help":
        await st.telegram.send(chat_id, "Ask me in English, Hinglish or Hindi: track an order, return something, or get a refund. "
                                        "Every refund is checked against the shop's records first. /orders shows your demo orders.")
        return
    if text.split("@")[0] == "/start":
        text = "namaste"
    await st.agent.handle(conv, text or "photo", media=media)


router = APIRouter()


@router.post("/webhooks/telegram")
async def webhook(request: Request):
    app = request.app
    if getattr(app.state, "telegram", None) is None:
        raise HTTPException(404, "Telegram is not configured")
    if not constant_time_equal(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), app.state.telegram_secret):
        raise HTTPException(403, "bad secret token")
    task = asyncio.create_task(process_update(app, await request.json()))
    app.state.bg_tasks.add(task)
    task.add_done_callback(app.state.bg_tasks.discard)
    return {"ok": True}


async def poll_loop(app) -> None:
    offset = 0
    while True:
        try:
            for upd in await app.state.telegram.call("getUpdates", offset=offset, timeout=25):
                offset = upd["update_id"] + 1
                await process_update(app, upd)
        except Exception as e:  # noqa: BLE001
            log.warning("telegram poll error: %s", type(e).__name__)
            await asyncio.sleep(3)

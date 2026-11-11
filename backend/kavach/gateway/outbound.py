"""Outbound messages to customers and sellers, routed by channel.

`send(conv, text)` stores the message and delivers it on the customer's channel (web via the live stream;
WhatsApp/Telegram via their adapters). `notify_seller(card)` puts an approval card on every seller channel
that is configured (console always; WhatsApp/Telegram when set up). Delivery failures are logged as
events and never crash the conversation.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Awaitable, Callable

import asyncpg

from kavach.agent import replies as R
from kavach.events import EventBus
from kavach.gateway.identity import record_message

log = logging.getLogger("kavach.outbound")
ChannelSender = Callable[[str, str, list[tuple[str, str]] | None], Awaitable[None]]   # (user_id, text, buttons)


class Outbound:
    def __init__(self, pool: asyncpg.Pool, bus: EventBus):
        self.pool, self.bus = pool, bus
        self.channels: dict[str, ChannelSender] = {}       # "whatsapp", "telegram"
        self.seller_targets: list[tuple[str, str]] = []     # [(channel, user_id)]
        self.seller_feed: deque = deque(maxlen=100)         # recent cards for the console

    async def send(self, conv: dict, text: str, trace_id: str | None = None) -> None:
        await record_message(self.pool, conv, "out", text)
        self.bus.message(conv.get("session"), "out", text, trace_id)
        sender = self.channels.get(conv["channel"])
        if sender:
            try:
                await sender(conv["user_id"], text, None)
            except Exception as e:  # noqa: BLE001
                log.warning("send failed on %s: %s", conv["channel"], type(e).__name__)
                if trace_id:
                    await self.bus.emit(trace_id, "reply", "fail", None, channel=conv["channel"], error=type(e).__name__)

    def card_text(self, card: dict) -> tuple[str, list[tuple[str, str]] | None]:
        conv = card.get("conv", {})
        who = conv.get("name", "A customer")
        if card["kind"] == "approval":
            amount = card["args"].get("amount_paise")
            what = f"{R.rs(amount)} refund" if amount else card["tool"].replace("_", " ")
            text = (f"🛡 Kavach: approval #{card['approval_id']}\n{who} — {what} on order {card['order']['id']} ({card['order']['item']}).\n"
                    f"All checks passed; needs you because it's over your auto-limit or flagged.\n"
                    f"Reply 1 to approve, 2 to reject.")
            return text, [("Approve", f"approve:{card['approval_id']}"), ("Reject", f"reject:{card['approval_id']}")]
        if card["kind"] == "human":
            return f"🙋 Kavach: {who} wants to talk to you.\n{card.get('summary', '')}", None
        return f"⚠️ Kavach: {card.get('summary', '')}", None

    async def notify_seller(self, card: dict) -> None:
        self.seller_feed.appendleft({k: v for k, v in card.items() if k != "conv"} | {"customer": card.get("conv", {}).get("name")})
        await self.bus.emit(card.get("trace_id", "seller"), "approve" if card["kind"] == "approval" else "route", "warn", None,
                            kind=card["kind"], approval_id=card.get("approval_id"))
        text, buttons = self.card_text(card)
        for channel, user_id in self.seller_targets:
            sender = self.channels.get(channel)
            if sender:
                try:
                    await sender(user_id, text, buttons)
                except Exception as e:  # noqa: BLE001
                    log.warning("seller notify failed on %s: %s", channel, type(e).__name__)

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


HELD = {"over_auto_limit": "it's above your auto-refund limit", "over_hard_cap": "it's above your ₹2,000 hard cap",
        "refund_frequency": "this customer had another refund this month", "guard_flag": "the message looked like pressure or a scam",
        "photo_unverified": "the photo needs a quick look", "instruction_in_record": "the order note contains a hidden instruction"}


def is_test_session(conv: dict) -> bool:
    """Sessions made by our own scripts (verify_*, test_*, eval_*) stay off real seller channels."""
    return conv.get("channel") == "web" and str(conv.get("user_id", "")).startswith(("verify_", "test_", "eval_"))


class Outbound:
    def __init__(self, pool: asyncpg.Pool, bus: EventBus):
        self.pool, self.bus = pool, bus
        self.channels: dict[str, ChannelSender] = {}       # "whatsapp", "telegram"
        self.seller_targets: list[tuple[str, str]] = []     # [(channel, user_id)]
        self.seller_feed: deque = deque(maxlen=100)         # recent cards for the console
        self.mailer = None
        self._mail_tasks: set = set()
        self._carded: dict[int, set[str]] = {}               # approval id -> seller channels that got the card
        self.calls = None                                    # SellerCalls (alert calls), set at startup when configured

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
            why = ", ".join(HELD.get(r, r.replace("_", " ")) for r in (card.get("reasons") or [])) or "it needs a person"
            link = f"\nReceipt: {R.WEB}/proof/{card['trace_id']}" if card.get("trace_id") else ""
            text = (f"🛡 *Approval needed · #{card['approval_id']}*\n{who} wants a {what} on order {card['order']['id']} ({card['order']['item']}).\n"
                    f"Records check out ✓ · held because {why}.\n\n"
                    f"Reply *1* to approve or *2* to reject.{link}")
            return text, [("Approve", f"approve:{card['approval_id']}"), ("Reject", f"reject:{card['approval_id']}")]
        if card["kind"] == "human":
            return f"🙋 Kavach: {who} wants to talk to you.\n{card.get('summary', '')}", None
        return f"⚠️ Kavach: {card.get('summary', '')}", None

    async def notify_seller(self, card: dict) -> None:
        self.seller_feed.appendleft({k: v for k, v in card.items() if k != "conv"} | {"customer": card.get("conv", {}).get("name")})
        await self.bus.emit(card.get("trace_id", "seller"), "approve" if card["kind"] == "approval" else "route", "warn", None,
                            kind=card["kind"], approval_id=card.get("approval_id"))
        text, buttons = self.card_text(card)
        conv = card.get("conv") or {}
        if is_test_session(conv):
            return  # automated test runs never reach the seller's real phone, inbox or paid messages
        # Budget: web-demo traffic (judges) goes to the free channels; WhatsApp to the seller costs money per message.
        skip = {"whatsapp"} if conv.get("channel") == "web" else set()
        if self.mailer is not None:
            import asyncio
            plain = text.replace("*", "")                    # email: no chat markup
            subject = "Kavach: " + plain.splitlines()[0].replace("🛡 ", "").replace("⚠️ ", "").replace("🙋 ", "").removeprefix("Kavach: ")
            task = asyncio.create_task(self.mailer.send(subject, plain.replace("Reply 1 to approve or 2 to reject.",
                                                                               "Approve or reject on WhatsApp/Telegram or in the seller console.")))
            self._mail_tasks.add(task)
            task.add_done_callback(self._mail_tasks.discard)
        for channel, user_id in self.seller_targets:
            sender = self.channels.get(channel)
            if sender and channel not in skip:
                try:
                    await sender(user_id, text, buttons)
                    if card.get("approval_id") is not None:
                        self._carded.setdefault(int(card["approval_id"]), set()).add(channel)
                except Exception as e:  # noqa: BLE001
                    log.warning("seller notify failed on %s: %s", channel, type(e).__name__)
        if self.calls is not None:
            await self.calls.on_card(card)

    async def broadcast_seller(self, text: str, exclude: str | None = None, approval_id: int | None = None) -> None:
        """Tell the seller's other channels that something was already handled (first decision wins).
        With an approval id, only channels that actually got that card are told."""
        got = self._carded.pop(approval_id, None) if approval_id is not None else None
        for channel, user_id in self.seller_targets:
            if channel == exclude or (got is not None and channel not in got):
                continue
            sender = self.channels.get(channel)
            if sender:
                try:
                    await sender(user_id, text, None)
                except Exception as e:  # noqa: BLE001
                    log.warning("seller broadcast failed on %s: %s", channel, type(e).__name__)

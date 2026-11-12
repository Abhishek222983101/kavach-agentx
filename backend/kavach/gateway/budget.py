"""Hard WhatsApp spend budget, persisted in Postgres so restarts can't reset it.

Twilio bills $0.005 per WhatsApp message sent OR received (pricing page, Nov 2026). The budget counts both.
Default: 98 free trial messages + $1 of paid messages (200) - a safety margin = 280 messages in total.
When it is reached, Kavach sends nothing more on WhatsApp (Telegram, web and email keep working).
Inbound messages are counted too but cannot be prevented: after the cap, each stranger's message costs at
most $0.005 and gets no reply.
"""
from __future__ import annotations

import os

import asyncpg

KEY = "whatsapp_messages"
PRICE_USD = 0.005


class WhatsAppBudget:
    def __init__(self, pool: asyncpg.Pool, limit: int | None = None):
        self.pool = pool
        self.limit = limit if limit is not None else int(os.getenv("WHATSAPP_MESSAGE_BUDGET", "280"))

    async def used(self) -> int:
        return int(await self.pool.fetchval("SELECT coalesce((SELECT n FROM usage_counters WHERE key = $1), 0)", KEY))

    async def charge(self) -> int:
        return int(await self.pool.fetchval(
            """INSERT INTO usage_counters(key, n) VALUES ($1, 1)
               ON CONFLICT (key) DO UPDATE SET n = usage_counters.n + 1 RETURNING n""", KEY))

    async def refund(self) -> None:
        await self.pool.execute("UPDATE usage_counters SET n = greatest(0, n - 1) WHERE key = $1", KEY)

    async def allow(self) -> bool:
        return await self.used() < self.limit

    async def summary(self) -> str:
        u = await self.used()
        return f"WhatsApp budget: {u}/{self.limit} messages used (≈ ${max(0, u - 98) * PRICE_USD:.2f} beyond the free 98)"

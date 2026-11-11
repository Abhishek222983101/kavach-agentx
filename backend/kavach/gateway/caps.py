"""Cost and abuse caps (D-14). In-memory per process, reset at midnight IST.

- per user: inbound messages handled per day (default 25; judges get room to play)
- global: outbound WhatsApp messages per day (default 300) to protect the Twilio balance
- global: LLM-backed turns per day (default 800) to stay inside free tiers
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


class Caps:
    def __init__(self) -> None:
        self.per_user = int(os.getenv("RATE_LIMIT_PER_USER_DAY", "25"))
        self.whatsapp_out = int(os.getenv("WHATSAPP_OUT_PER_DAY", "300"))
        self.llm_turns = int(os.getenv("GLOBAL_DAILY_LLM_BUDGET", "800"))
        self.new_customers = int(os.getenv("NEW_DEMO_CUSTOMERS_PER_DAY", "300"))
        self._new = 0
        self._day = self._today()
        self._users: dict[str, int] = defaultdict(int)
        self._wa_out = 0
        self._turns = 0

    @staticmethod
    def _today() -> str:
        return datetime.now(IST).strftime("%Y-%m-%d")

    def _roll(self) -> None:
        if (d := self._today()) != self._day:
            self._day, self._users, self._wa_out, self._turns, self._new = d, defaultdict(int), 0, 0, 0

    def allow_user(self, key: str) -> bool:
        self._roll()
        if self._users[key] >= self.per_user or self._turns >= self.llm_turns:
            return False
        self._users[key] += 1
        self._turns += 1
        return True

    def allow_whatsapp_out(self) -> bool:
        self._roll()
        if self._wa_out >= self.whatsapp_out:
            return False
        self._wa_out += 1
        return True

    def allow_new_customer(self) -> bool:
        self._roll()
        if self._new >= self.new_customers:
            return False
        self._new += 1
        return True

    def snapshot(self) -> dict:
        self._roll()
        return {"day": self._day, "users": len(self._users), "turns": self._turns, "whatsapp_out": self._wa_out,
                "limits": {"per_user": self.per_user, "whatsapp_out": self.whatsapp_out, "llm_turns": self.llm_turns}}

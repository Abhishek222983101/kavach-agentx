"""Runtime configuration, read once from the environment (.env in development).

Every value has a safe default for local development except secrets, which must be set explicitly
in production (see `require`). Nothing here is ever logged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    env: str
    database_url_owner: str      # migrations and seeding only
    database_url_reader: str     # agent / api process (read + limited inserts)
    database_url_writer: str     # store + trust service (writes)
    store_url: str
    trust_url: str
    store_reader_key: str
    store_writer_key: str
    trust_api_key: str           # api process -> trust service
    verdict_secret: str          # HMAC key for signed verdicts; ONLY the trust service loads it
    seller_console_pin: str
    allow_ttl_s: int
    approved_ttl_s: int
    daily_write_cap: int
    daily_refund_cap_paise: int


@lru_cache
def settings() -> Settings:
    owner = os.getenv("DATABASE_URL", "")
    return Settings(
        env=os.getenv("KAVACH_ENV", "dev"),
        database_url_owner=owner,
        database_url_reader=os.getenv("DATABASE_URL_READER", owner),
        database_url_writer=os.getenv("DATABASE_URL_WRITER", owner),
        store_url=os.getenv("STORE_URL", "http://127.0.0.1:8200"),
        trust_url=os.getenv("TRUST_URL", "http://127.0.0.1:8100"),
        store_reader_key=os.getenv("STORE_READER_KEY", ""),
        store_writer_key=os.getenv("STORE_WRITER_KEY", ""),
        trust_api_key=os.getenv("TRUST_API_KEY", ""),
        verdict_secret=os.getenv("VERDICT_SECRET", ""),
        seller_console_pin=os.getenv("SELLER_CONSOLE_PIN", ""),
        allow_ttl_s=_int("ALLOW_TTL_S", 60),
        approved_ttl_s=_int("APPROVED_TTL_S", 24 * 3600),
        daily_write_cap=_int("DAILY_WRITE_CAP", 200),
        daily_refund_cap_paise=_int("DAILY_REFUND_CAP_PAISE", 50_000_00),
    )


def require(value: str, name: str) -> str:
    """Fail fast at startup if a secret is missing or too weak."""
    if len(value) < 16:
        raise RuntimeError(f"{name} is missing or shorter than 16 characters; set it in .env")
    return value

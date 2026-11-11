"""asyncpg pools with JSON codecs. One pool per role; each process opens only the role it needs."""
from __future__ import annotations

import json

import asyncpg


async def _init(conn: asyncpg.Connection) -> None:
    for typ in ("json", "jsonb"):
        await conn.set_type_codec(typ, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def create_pool(dsn: str, *, min_size: int = 1, max_size: int = 5) -> asyncpg.Pool:
    if not dsn:
        raise RuntimeError("database URL is not configured")
    return await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size, init=_init,
                                     command_timeout=10, max_inactive_connection_lifetime=30)  # recycle before Neon idles out

"""Who is this chat? Map (channel, user id) to a customer, creating a demo customer on first contact."""
from __future__ import annotations

import asyncpg

from kavach.agent.trust_client import TrustClient


class TooManyNewCustomers(Exception):
    pass


async def resolve(pool: asyncpg.Pool, trust: TrustClient, channel: str, user_id: str, name: str | None = None,
                  allow_new=lambda: True) -> dict:
    row = await pool.fetchrow(
        """SELECT c.customer_id, cu.name, cu.lang FROM conversations c JOIN customers cu ON cu.id = c.customer_id
           WHERE c.channel = $1 AND c.user_id = $2""", channel, user_id)
    if row is None:
        if not allow_new():
            raise TooManyNewCustomers()
        prov = await trust.provision(channel, user_id, name)
        await pool.execute("""INSERT INTO conversations(channel, user_id, customer_id) VALUES ($1,$2,$3)
                              ON CONFLICT (channel, user_id) DO NOTHING""", channel, user_id, prov["customer_id"])
        row = await pool.fetchrow(
            """SELECT c.customer_id, cu.name, cu.lang FROM conversations c JOIN customers cu ON cu.id = c.customer_id
               WHERE c.channel = $1 AND c.user_id = $2""", channel, user_id)
    return {"channel": channel, "user_id": user_id, "customer_id": row["customer_id"], "name": row["name"], "lang": row["lang"]}


async def record_message(pool: asyncpg.Pool, conv: dict, direction: str, text: str, provider_msg_id: str | None = None,
                         media: list | None = None) -> bool:
    """Store a message. Returns False if provider_msg_id was already seen (duplicate webhook)."""
    try:
        await pool.execute(
            """INSERT INTO messages(conversation_id, direction, text, media, provider_msg_id)
               SELECT id, $3, $4, $5::jsonb, $6 FROM conversations WHERE channel = $1 AND user_id = $2""",
            conv["channel"], conv["user_id"], direction, text[:2000], media, provider_msg_id)
        return True
    except asyncpg.UniqueViolationError:
        return False

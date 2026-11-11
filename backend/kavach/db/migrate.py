"""Apply the schema, create the two least-privilege roles, and apply grants.

    uv run python -m kavach.db.migrate            # uses DATABASE_URL (owner) from .env
    uv run python -m kavach.db.migrate --reset    # also wipes data (demo reset; audit_log kept unless --hard)

Role passwords are generated here (hex only, so they are safe to inline in DDL) and their connection
strings are written to .env as DATABASE_URL_READER / DATABASE_URL_WRITER. Nothing secret is printed.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import secrets
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import asyncpg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ROLES = ("kavach_reader", "kavach_writer")
DATA_TABLES = (
    "events", "attack_runs", "eval_runs", "seller_precedents", "executions", "approvals", "verdicts", "proposals",
    "messages", "conversations", "photos", "returns", "refunds", "payments", "shipments", "orders", "customers",
    "policy_clauses", "settings",
)


def role_dsn(owner_dsn: str, role: str, password: str) -> str:
    u = urlsplit(owner_dsn)
    host = u.hostname or "localhost"
    netloc = f"{role}:{quote(password)}@{host}" + (f":{u.port}" if u.port else "")
    return urlunsplit((u.scheme, netloc, u.path, u.query, u.fragment))


async def ensure_role(conn: asyncpg.Connection, role: str, password: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{32,64}", password):
        raise ValueError("role passwords must be lowercase hex")
    exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", role)
    verb = "ALTER" if exists else "CREATE"
    # role names come from the fixed ROLES tuple; password is validated hex above
    await conn.execute(f"{verb} ROLE {role} WITH LOGIN PASSWORD '{password}'")


CHECKPOINT_TABLES = ("checkpoint_migrations", "checkpoints", "checkpoint_blobs", "checkpoint_writes")


async def _checkpointer_tables(owner_dsn: str, conn: asyncpg.Connection) -> None:
    """Create LangGraph's Postgres checkpoint tables (as owner) and let the agent's reader role use them."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(owner_dsn) as saver:
        await saver.setup()
    for t in CHECKPOINT_TABLES:  # fixed names, not user input
        await conn.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {t} TO kavach_reader")


async def migrate(owner_dsn: str, passwords: dict[str, str], reset: bool = False, hard: bool = False) -> None:
    conn = await asyncpg.connect(owner_dsn)
    try:
        await conn.execute((HERE / "schema.sql").read_text())
        for role in ROLES:
            await ensure_role(conn, role, passwords[role])
        await conn.execute((HERE / "roles.sql").read_text())
        await _checkpointer_tables(owner_dsn, conn)
        if reset:
            await conn.execute("TRUNCATE " + ", ".join(DATA_TABLES) + " RESTART IDENTITY CASCADE")
            if hard:  # TRUNCATE bypasses the row trigger by design; only the owner can do it
                await conn.execute("TRUNCATE audit_log RESTART IDENTITY")
    finally:
        await conn.close()


def _update_env(values: dict[str, str]) -> None:
    env = ROOT / ".env"
    text = env.read_text() if env.exists() else ""
    for k, v in values.items():
        line = f"{k}={v}"
        text = re.sub(rf"^{k}=.*$", line, text, flags=re.M) if re.search(rf"^{k}=", text, re.M) else text + line + "\n"
    env.write_text(text)
    env.chmod(0o600)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--hard", action="store_true")
    args = ap.parse_args()
    owner = os.environ["DATABASE_URL"]
    passwords: dict[str, str] = {}
    new_env: dict[str, str] = {}
    for role, var in zip(ROLES, ("DATABASE_URL_READER", "DATABASE_URL_WRITER")):
        existing = os.getenv(var, "")
        m = re.match(rf"^[a-z]+://{role}:([0-9a-f]+)@", existing)
        passwords[role] = m.group(1) if m else secrets.token_hex(24)
        new_env[var] = role_dsn(owner, role, passwords[role])
    asyncio.run(migrate(owner, passwords, reset=args.reset, hard=args.hard))
    _update_env(new_env)
    print("migrated; roles:", ", ".join(ROLES), "| reset:" , args.reset, "| role URLs written to .env")


if __name__ == "__main__":
    main()

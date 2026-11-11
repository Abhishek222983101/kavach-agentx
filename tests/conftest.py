"""Test harness: a throwaway Postgres 18 in Docker with the real schema and roles.

Tests never touch Neon. The container is created once per session and removed afterwards
(set KAVACH_KEEP_TEST_DB=1 to keep it for debugging).
"""
from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import time

import asyncpg
import pytest

from kavach.db import migrate as mig
from kavach.db.pool import create_pool

CONTAINER = "kavach-test-pg"
PASSWORDS = {"kavach_reader": "a1" * 16, "kavach_writer": "b2" * 16}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def pg_dsns():
    if not shutil.which("docker"):
        pytest.skip("docker not available")
    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
    port = _free_port()
    subprocess.run(["docker", "run", "-d", "--name", CONTAINER, "-e", "POSTGRES_PASSWORD=owner",
                    "-p", f"127.0.0.1:{port}:5432", "postgres:18"], check=True, capture_output=True)
    owner = f"postgresql://postgres:owner@127.0.0.1:{port}/postgres"

    async def wait() -> None:
        deadline = time.time() + 60
        while True:
            try:
                c = await asyncpg.connect(owner)
                await c.close()
                return
            except Exception:
                if time.time() > deadline:
                    raise
                await asyncio.sleep(0.5)

    asyncio.run(wait())
    asyncio.run(mig.migrate(owner, PASSWORDS))
    yield {
        "owner": owner,
        "reader": mig.role_dsn(owner, "kavach_reader", PASSWORDS["kavach_reader"]),
        "writer": mig.role_dsn(owner, "kavach_writer", PASSWORDS["kavach_writer"]),
    }
    if not os.getenv("KAVACH_KEEP_TEST_DB"):
        subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)


@pytest.fixture(scope="session")
async def pools(pg_dsns):
    p = {k: await create_pool(v) for k, v in pg_dsns.items()}
    yield p
    for pool in p.values():
        await pool.close()

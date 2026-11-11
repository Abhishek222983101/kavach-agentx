"""Phase 0 acceptance: least privilege and the append-only audit log are enforced by the database itself."""
import asyncpg
import pytest


async def test_reader_cannot_move_money(pools):
    async with pools["reader"].acquire() as c:
        for sql in (
            "INSERT INTO refunds(order_id, amount_paise, idempotency_key) VALUES (1, 100, 'x')",
            "UPDATE orders SET refunded_paise = 0",
            "UPDATE settings SET value = '0'",
            "INSERT INTO executions(proposal_id, nonce, tool, result) VALUES ('p','n','t','{}')",
            "INSERT INTO proposals(id, trace_id, tool, args, args_hash, claims, caller) VALUES ('p','t','x','{}','h','[]','{}')",
        ):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await c.execute(sql)


async def test_nobody_inserts_into_audit_directly(pools):
    for role in ("reader", "writer"):
        async with pools[role].acquire() as c:
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await c.execute("INSERT INTO audit_log(ts,event,summary,payload,prev_hash,hash) VALUES (now(),'e','s','{}','0','h')")


async def test_audit_chain_appends_verifies_and_refuses_edits(pools):
    async with pools["writer"].acquire() as c:
        for n in range(3):
            await c.fetchval("SELECT audit_append($1, $2, $3::jsonb)", "test", f"row {n}", {"n": n, "₹": "१२"})
        assert await c.fetchval("SELECT audit_verify('audit_log')") is None
        # layer 1: app roles have no UPDATE/DELETE privilege at all
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await c.execute("UPDATE audit_log SET summary = 'forged' WHERE i = 1")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await c.execute("DELETE FROM audit_log WHERE i = 1")
    # layer 2: even the database owner is stopped by the trigger
    async with pools["owner"].acquire() as c:
        with pytest.raises(asyncpg.RaiseError, match="append-only"):
            await c.execute("UPDATE audit_log SET summary = 'forged' WHERE i = 1")
        with pytest.raises(asyncpg.RaiseError, match="append-only"):
            await c.execute("DELETE FROM audit_log WHERE i = 1")


async def test_tampered_copy_is_detected(pools):
    async with pools["owner"].acquire() as c:
        async with c.transaction():
            await c.execute("CREATE TEMP TABLE audit_copy AS SELECT * FROM audit_log")
            await c.execute("UPDATE audit_copy SET summary = 'refund ₹50,000 approved' WHERE i = 2")
            assert await c.fetchval("SELECT audit_verify('audit_copy')") == 2
            await c.execute("DROP TABLE audit_copy")

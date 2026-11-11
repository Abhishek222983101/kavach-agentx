"""Mock Store API: the system of record (ARCH §9.6). Runs as its own process on localhost.

Shopify-shaped orders, Shiprocket-shaped shipments, Razorpay-shaped refunds, all fake data.
- Every request needs X-Api-Key: the reader key can only GET; the writer key (held by the trust
  service alone) is required for anything that changes state.
- Every write needs an Idempotency-Key. Replaying the same key returns the first result; reusing a key
  with different content is refused (409).
- The store enforces its own integrity rules (never refund more than was paid, no address change after
  dispatch) as defence in depth; the verifier is the main gate, not the only one.
- Chaos switches (writer key) simulate a courier outage, latency or flaky responses for the demo.
"""
from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from typing import Any, Literal

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from kavach.common.canonical import canonical, constant_time_equal, sha256_hex
from kavach.common.config import require, settings
from kavach.db.pool import create_pool

Role = Literal["reader", "writer"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RefundIn(_In):
    order_id: int = Field(gt=0)
    amount_paise: int = Field(gt=0, le=10_000_000)


class ReturnIn(_In):
    order_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=40)


class AddressIn(_In):
    new_address: str = Field(min_length=6, max_length=300)


class SettingIn(_In):
    value: bool | int


class ChaosIn(_In):
    courier_down: bool = False
    latency_ms: int = Field(default=0, ge=0, le=10_000)
    flaky_rate: float = Field(default=0.0, ge=0.0, le=1.0)


EDITABLE_SETTINGS = {"auto_limit_paise", "window_days", "hard_cap_paise", "kill_switch"}


def create_app(*, reader_pool: asyncpg.Pool | None = None, writer_pool: asyncpg.Pool | None = None,
               reader_key: str | None = None, writer_key: str | None = None) -> FastAPI:
    cfg = settings()
    keys = {"reader": reader_key or cfg.store_reader_key, "writer": writer_key or cfg.store_writer_key}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owned = []
        if app.state.rpool is None:
            app.state.rpool = await create_pool(cfg.database_url_reader); owned.append(app.state.rpool)
        if app.state.wpool is None:
            app.state.wpool = await create_pool(cfg.database_url_writer); owned.append(app.state.wpool)
        yield
        for p in owned:
            await p.close()

    app = FastAPI(title="Kavach mock store", version="1.0", lifespan=lifespan, docs_url="/docs" if cfg.env == "dev" else None, redoc_url=None)  # interactive docs only in dev
    app.state.rpool, app.state.wpool = reader_pool, writer_pool
    app.state.chaos = ChaosIn()
    for name, key in keys.items():
        require(key, f"STORE_{name.upper()}_KEY")

    def role_of(x_api_key: str = Header(default="")) -> Role:
        if constant_time_equal(x_api_key, keys["writer"]):
            return "writer"
        if constant_time_equal(x_api_key, keys["reader"]):
            return "reader"
        raise HTTPException(401, "missing or invalid API key")

    def writer(role: Role = Depends(role_of)) -> Role:
        if role != "writer":
            raise HTTPException(403, "writer key required")
        return role

    def idem(idempotency_key: str = Header(default="")) -> str:
        if not (8 <= len(idempotency_key) <= 128):
            raise HTTPException(400, "Idempotency-Key header (8-128 chars) required")
        return idempotency_key

    async def courier_gate() -> None:
        c: ChaosIn = app.state.chaos
        if c.latency_ms:
            await asyncio.sleep(c.latency_ms / 1000)
        if c.courier_down or (c.flaky_rate and random.random() < c.flaky_rate):  # noqa: S311 - demo chaos, not crypto
            raise HTTPException(503, "courier API unavailable")

    rp = lambda: app.state.rpool  # noqa: E731
    wp = lambda: app.state.wpool  # noqa: E731

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "chaos": app.state.chaos.model_dump()}

    # ───────────── reads ─────────────
    @app.get("/customers/{cid}")
    async def customer(cid: str, _: Role = Depends(role_of)):
        row = await rp().fetchrow("SELECT id, name, phone, lang FROM customers WHERE id = $1", cid)
        if not row:
            raise HTTPException(404, "customer not found")
        return dict(row)

    @app.get("/customers")
    async def customer_by(phone: str | None = Query(default=None, max_length=20),
                          tg_id: int | None = None, _: Role = Depends(role_of)):
        if phone:
            row = await rp().fetchrow("SELECT id, name, phone, lang FROM customers WHERE phone = $1", phone)
        elif tg_id is not None:
            row = await rp().fetchrow("SELECT id, name, phone, lang FROM customers WHERE tg_id = $1", tg_id)
        else:
            raise HTTPException(400, "phone or tg_id required")
        if not row:
            raise HTTPException(404, "customer not found")
        return dict(row)


    @app.get("/orders/{oid}")
    async def order(oid: int, _: Role = Depends(role_of)):
        row = await rp().fetchrow("SELECT id, customer_id, item, category, paid_paise, refunded_paise, status, cod, perishable, note, address, awb, created_at FROM orders WHERE id = $1", oid)
        if not row:
            raise HTTPException(404, "order not found")
        return dict(row)

    @app.get("/orders")
    async def orders(customer_id: str = Query(min_length=1, max_length=64), limit: int = Query(default=10, ge=1, le=50),
                     _: Role = Depends(role_of)):
        rows = await rp().fetch(
            "SELECT id, customer_id, item, category, paid_paise, refunded_paise, status, cod, perishable, note, address, awb, created_at FROM orders WHERE customer_id = $1 ORDER BY created_at DESC LIMIT $2", customer_id, limit)
        return [dict(r) for r in rows]

    @app.get("/shipments/{awb}")
    async def shipment(awb: str, _: Role = Depends(role_of)):
        await courier_gate()
        row = await rp().fetchrow("SELECT awb, order_id, courier, status, delivered_at, events FROM shipments WHERE awb = $1", awb)
        if not row:
            raise HTTPException(404, "shipment not found")
        return dict(row)

    @app.get("/refunds")
    async def refunds(order_id: int | None = None, customer_id: str | None = Query(default=None, max_length=64),
                      days: int = Query(default=30, ge=1, le=365), _: Role = Depends(role_of)):
        if order_id is not None:
            rows = await rp().fetch("SELECT id, order_id, amount_paise, created_at FROM refunds WHERE order_id = $1 ORDER BY created_at", order_id)
        elif customer_id:
            rows = await rp().fetch(
                """SELECT r.id, r.order_id, r.amount_paise, r.created_at FROM refunds r JOIN orders o ON o.id = r.order_id
                   WHERE o.customer_id = $1 AND r.created_at > now() - make_interval(days => $2) ORDER BY r.created_at""",
                customer_id, days)
        else:
            raise HTTPException(400, "order_id or customer_id required")
        return [dict(r) for r in rows]

    @app.get("/policies")
    async def policies(_: Role = Depends(role_of)):
        return [dict(r) for r in await rp().fetch("SELECT id, title, text, text_hinglish FROM policy_clauses ORDER BY id")]

    @app.get("/photos")
    async def photos(order_id: int, _: Role = Depends(role_of)):
        return [dict(r) for r in await rp().fetch("SELECT id, order_id, phash, ai_score, uploaded_at FROM photos WHERE order_id = $1", order_id)]

    @app.get("/settings")
    async def get_settings(_: Role = Depends(role_of)):
        return {r["key"]: r["value"] for r in await rp().fetch("SELECT key, value FROM settings")}

    # ───────────── writes (writer key + idempotency) ─────────────
    async def _replay(conn: asyncpg.Connection, table: str, key: str, fingerprint: str) -> dict | None:
        sql = {"refunds": "SELECT * FROM refunds WHERE idempotency_key = $1",
               "returns": "SELECT * FROM returns WHERE idempotency_key = $1"}[table]
        row = await conn.fetchrow(sql, key)
        if row is None:
            return None
        stored = {k: row[k] for k in ("order_id", "amount_paise", "reason") if k in row.keys()}
        if sha256_hex(canonical(stored)) != fingerprint:
            raise HTTPException(409, "Idempotency-Key reused with different content")
        return {**dict(row), "replayed": True}

    @app.post("/refunds")
    async def create_refund(body: RefundIn, key: str = Depends(idem), _: Role = Depends(writer)):
        fp = sha256_hex(canonical({"order_id": body.order_id, "amount_paise": body.amount_paise}))
        async with wp().acquire() as conn, conn.transaction():
            if (prev := await _replay(conn, "refunds", key, fp)) is not None:
                return prev
            o = await conn.fetchrow("SELECT paid_paise, refunded_paise FROM orders WHERE id = $1 FOR UPDATE", body.order_id)
            if not o:
                raise HTTPException(404, "order not found")
            if body.amount_paise > o["paid_paise"] - o["refunded_paise"]:
                raise HTTPException(422, "refund exceeds the refundable amount")
            row = await conn.fetchrow("INSERT INTO refunds(order_id, amount_paise, idempotency_key) VALUES ($1,$2,$3) RETURNING *",
                                      body.order_id, body.amount_paise, key)
            await conn.execute("UPDATE orders SET refunded_paise = refunded_paise + $1 WHERE id = $2", body.amount_paise, body.order_id)
            return {**dict(row), "replayed": False}

    @app.post("/returns")
    async def create_return(body: ReturnIn, key: str = Depends(idem), _: Role = Depends(writer)):
        fp = sha256_hex(canonical({"order_id": body.order_id, "reason": body.reason}))
        async with wp().acquire() as conn, conn.transaction():
            if (prev := await _replay(conn, "returns", key, fp)) is not None:
                return prev
            o = await conn.fetchrow("SELECT status, perishable FROM orders WHERE id = $1 FOR UPDATE", body.order_id)
            if not o:
                raise HTTPException(404, "order not found")
            if o["status"] != "delivered" or o["perishable"]:
                raise HTTPException(422, "order is not returnable")
            row = await conn.fetchrow("INSERT INTO returns(order_id, reason, idempotency_key) VALUES ($1,$2,$3) RETURNING *",
                                      body.order_id, body.reason, key)
            return {**dict(row), "replayed": False}

    async def _pre_dispatch_update(oid: int, sql: str, *args: Any) -> dict:
        async with wp().acquire() as conn, conn.transaction():
            o = await conn.fetchrow("SELECT status FROM orders WHERE id = $1 FOR UPDATE", oid)
            if not o:
                raise HTTPException(404, "order not found")
            if o["status"] not in ("placed", "packed"):
                raise HTTPException(422, f"order already {o['status']}")
            row = await conn.fetchrow(sql, oid, *args)
            return dict(row)

    @app.patch("/orders/{oid}/address")
    async def update_address(oid: int, body: AddressIn, _k: str = Depends(idem), _: Role = Depends(writer)):
        return await _pre_dispatch_update(oid, "UPDATE orders SET address = $2 WHERE id = $1 RETURNING id, address, status", body.new_address)

    @app.post("/orders/{oid}/cancel")
    async def cancel(oid: int, _k: str = Depends(idem), _: Role = Depends(writer)):
        return await _pre_dispatch_update(oid, "UPDATE orders SET status = 'cancelled' WHERE id = $1 RETURNING id, status")

    @app.put("/settings/{name}")
    async def put_setting(name: str, body: SettingIn, _: Role = Depends(writer)):
        if name not in EDITABLE_SETTINGS:
            raise HTTPException(404, "unknown setting")
        if name == "kill_switch" and not isinstance(body.value, bool):
            raise HTTPException(422, "kill_switch must be true or false")
        if name != "kill_switch" and (isinstance(body.value, bool) or not (0 < int(body.value) <= 10_000_000)):
            raise HTTPException(422, "value out of range")
        await wp().execute("INSERT INTO settings(key, value) VALUES ($1, $2::jsonb) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                           name, body.value)
        return {name: body.value}

    @app.post("/admin/chaos")
    async def chaos(body: ChaosIn, _: Role = Depends(writer)):
        app.state.chaos = body
        return body.model_dump()

    @app.exception_handler(asyncpg.PostgresError)
    async def db_error(_: Request, exc: asyncpg.PostgresError):  # never leak SQL details
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "store database error"}, status_code=500)

    return app

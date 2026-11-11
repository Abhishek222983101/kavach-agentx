"""The public API process: web chat, live events (SSE), seller console, channel webhooks (Phase 4).

It runs the agent with the READER database role and the store READER key. It holds no signing secret:
every change goes through the trust service (localhost). The seller PIN is only used to forward a
seller's own settings changes and approvals; judges can approve requests from their *own* demo chat.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from kavach import llm
from kavach.agent.graph import Agent, Deps
from kavach.agent.trust_client import TrustClient
from kavach.common.canonical import constant_time_equal
from kavach.common.config import require, settings
from kavach.events import EventBus
from kavach.gateway.caps import Caps
from kavach.gateway.identity import TooManyNewCustomers, record_message, resolve
from kavach.gateway.outbound import Outbound
from kavach.store.client import StoreClient

SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(default="", max_length=1000)
    photo: bool = False


class DecideIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]
    edited_amount_paise: int | None = Field(default=None, gt=0, le=10_000_000)


class SettingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Literal["kill_switch", "auto_limit_paise"]
    value: bool | int


def clean(text: str) -> str:
    return _CTRL.sub("", text).strip()


async def _open_checkpointer(dsn: str):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    pool = AsyncConnectionPool(dsn, open=False, min_size=1, max_size=5,
                               kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row})
    await pool.open()
    return AsyncPostgresSaver(pool), pool


def create_app(*, pool=None, store: StoreClient | None = None, trust: TrustClient | None = None,
               checkpointer: Any = None, seller_pin: str | None = None) -> FastAPI:
    cfg = settings()
    pin = seller_pin if seller_pin is not None else cfg.seller_console_pin

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from kavach.db.pool import create_pool

        owned: list = []
        st = app.state
        if st.pool is None:
            st.pool = await create_pool(cfg.database_url_reader); owned.append(st.pool)
        if st.store is None:
            st.store = StoreClient(cfg.store_url, require(cfg.store_reader_key, "STORE_READER_KEY")); owned.append(st.store)
        if st.trust is None:
            st.trust = TrustClient(cfg.trust_url, require(cfg.trust_api_key, "TRUST_API_KEY")); owned.append(st.trust)
        if st.checkpointer is None:
            st.checkpointer, cp_pool = await _open_checkpointer(cfg.database_url_reader); owned.append(cp_pool)
        st.bus = EventBus(st.pool)
        st.out = Outbound(st.pool, st.bus)
        st.agent = Agent(Deps(pool=st.pool, store=st.store, trust=st.trust, bus=st.bus, send=st.out.send,
                              notify_seller=st.out.notify_seller), st.checkpointer)
        st.caps = Caps()
        for hook in st.startup_hooks:          # channel adapters register here (Phase 4)
            await hook(app)
        yield
        await st.bus.drain()
        for o in owned:
            await (o.aclose() if hasattr(o, "aclose") else o.close())

    app = FastAPI(title="Kavach API", version="1.0", lifespan=lifespan,
                  docs_url="/docs" if cfg.env == "dev" else None, redoc_url=None)
    app.state.pool, app.state.store, app.state.trust, app.state.checkpointer = pool, store, trust, checkpointer
    app.state.startup_hooks = []
    origins = [o.strip() for o in os.getenv("WEB_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type", "X-Session", "X-Seller-Pin"], max_age=600)

    def session(x_session: str = Header(default="")) -> str:
        if not SESSION_RE.match(x_session):
            raise HTTPException(400, "X-Session header (16-64 letters, digits, - or _) required")
        return x_session

    def is_seller(x_seller_pin: str = Header(default="")) -> bool:
        return bool(pin) and constant_time_equal(x_seller_pin, pin)

    async def web_conv(sess: str) -> dict:
        try:
            conv = await resolve(app.state.pool, app.state.trust, "web", sess, allow_new=app.state.caps.allow_new_customer)
        except TooManyNewCustomers:
            raise HTTPException(429, "the demo is very busy today; please try again tomorrow") from None
        return {**conv, "session": sess}

    @app.exception_handler(Exception)
    async def unhandled(_: Request, e: Exception):   # never leak internals
        return JSONResponse({"detail": "something went wrong; please try again"}, status_code=500)

    # ───────────── health ─────────────
    @app.get("/health")
    async def health():
        counts: dict[str, int] = {}
        for p in llm.providers():
            counts[p.name] = counts.get(p.name, 0) + 1
        return {"status": "ok", "llm_keys": counts}

    # ───────────── web chat ─────────────
    @app.post("/api/chat")
    async def chat(body: ChatIn, sess: str = Depends(session)):
        text = clean(body.text)
        if not text and not body.photo:
            raise HTTPException(422, "empty message")
        conv = await web_conv(sess)
        if not app.state.caps.allow_user(f"web:{sess}"):
            return {"reply": "You've reached today's demo limit for this chat. Please try again tomorrow.", "limited": True}
        media = [{"kind": "image", "content_type": "image/jpeg", "sha256": f"web-demo-photo-{sess}-{time.time_ns()}"}] if body.photo else []
        await record_message(app.state.pool, conv, "in", text or "[photo]", media=media or None)
        app.state.bus.message(sess, "in", text or "📷 photo")
        return await app.state.agent.handle(conv, text or "photo", media=media)

    @app.get("/api/me")
    async def me(sess: str = Depends(session)):
        conv = await web_conv(sess)
        orders = await app.state.store.orders(conv["customer_id"], limit=10)
        return {"customer_id": conv["customer_id"], "name": conv["name"],
                "orders": [{"id": o["id"], "item": o["item"], "status": o["status"], "paid_paise": o["paid_paise"],
                            "refunded_paise": o["refunded_paise"]} for o in orders]}

    @app.get("/api/chat/history")
    async def history(sess: str = Depends(session)):
        rows = await app.state.pool.fetch(
            """SELECT m.direction, m.text, m.ts FROM messages m JOIN conversations c ON c.id = m.conversation_id
               WHERE c.channel = 'web' AND c.user_id = $1 ORDER BY m.id DESC LIMIT 50""", sess)
        return [dict(r) for r in reversed(rows)]

    # ───────────── live events (SSE) ─────────────
    @app.get("/api/events")
    async def events(request: Request, session: str | None = None):
        if session is not None and not SESSION_RE.match(session):
            raise HTTPException(400, "bad session")
        if app.state.bus.viewers() >= int(os.getenv("MAX_LIVE_VIEWERS", "200")):
            raise HTTPException(503, "too many live viewers right now")
        sub = app.state.bus.subscribe(session)

        async def stream():
            try:
                yield "retry: 3000\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        msg = await asyncio.wait_for(sub.queue.get(), timeout=15)
                        yield f"data: {json.dumps(msg, default=str, ensure_ascii=False)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                app.state.bus.unsubscribe(sub)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ───────────── approvals: seller (PIN) or the judge for their own demo chat ─────────────
    async def _approval_owner(approval_id: int) -> str | None:
        return await app.state.pool.fetchval(
            "SELECT p.caller->>'customer_id' FROM approvals a JOIN proposals p ON p.id = a.proposal_id WHERE a.id = $1", approval_id)

    @app.get("/api/approvals")
    async def approvals(x_session: str = Header(default=""), seller: bool = Depends(is_seller)):
        rows = await app.state.trust.approvals("pending")
        if seller:
            return rows
        if not SESSION_RE.match(x_session):
            raise HTTPException(401, "seller PIN or demo session required")
        conv = await web_conv(x_session)
        return [r for r in rows if (r.get("caller") or {}).get("customer_id") == conv["customer_id"]]

    @app.post("/api/approvals/{approval_id}/decide")
    async def decide(approval_id: int, body: DecideIn, x_session: str = Header(default=""), seller: bool = Depends(is_seller)):
        via = "console"
        if not seller:
            if not SESSION_RE.match(x_session):
                raise HTTPException(401, "seller PIN or demo session required")
            conv = await web_conv(x_session)
            if await _approval_owner(approval_id) != conv["customer_id"]:
                raise HTTPException(403, "you can only decide approvals from your own demo chat")
        res = await app.state.agent.decide(approval_id, {"decision": body.decision, "decided_via": via,
                                                         "edited_amount_paise": body.edited_amount_paise})
        if res.get("status") == "not_pending":
            raise HTTPException(409, "already decided")
        return res

    @app.post("/api/seller/settings")
    async def seller_settings(body: SettingIn, seller: bool = Depends(is_seller)):
        if not seller:
            raise HTTPException(403, "seller PIN required")
        status, out = await app.state.trust.set_setting(body.name, body.value, pin, "console")
        if status != 200:
            raise HTTPException(status, out.get("detail", "refused"))
        return out

    @app.get("/api/seller/feed")
    async def seller_feed(seller: bool = Depends(is_seller)):
        if not seller:
            raise HTTPException(403, "seller PIN required")
        return list(app.state.out.seller_feed)

    # ───────────── proof for the judge page ─────────────
    @app.get("/api/stats")
    async def stats():
        row = await app.state.pool.fetchrow(
            """SELECT count(*) FILTER (WHERE verdict='ALLOW') AS allowed, count(*) FILTER (WHERE verdict='ESCALATE') AS escalated,
                      count(*) FILTER (WHERE verdict='BLOCK') AS blocked,
                      coalesce(sum((p.args->>'amount_paise')::bigint) FILTER (WHERE verdict='BLOCK'), 0) AS paise_blocked
               FROM verdicts v JOIN proposals p ON p.id = v.proposal_id WHERE p.parent_id IS NULL""")
        executed = await app.state.pool.fetchval(
            "SELECT coalesce(sum(amount_paise),0) FROM executions WHERE result->>'status' = 'done'")
        return {**dict(row), "paise_refunded": executed, "caps": app.state.caps.snapshot()}

    @app.get("/api/audit/verify")
    async def audit_verify():
        return await app.state.trust.audit_verify()

    return app

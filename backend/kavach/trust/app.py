"""HTTP face of the trust service. Listens on localhost only; the api process is its only client.

Auth: every call needs X-Api-Key = TRUST_API_KEY. Changing seller settings (kill switch, limits) also
needs X-Seller-Pin, so even the api process cannot raise a limit on its own.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from kavach.common.canonical import constant_time_equal
from kavach.common.config import require, settings
from kavach.common.contracts import Decision, ExecuteIn, ExecuteOut, ProposalIn, VerdictOut
from kavach.db.pool import create_pool
from kavach.store.client import StoreClient
from kavach.trust.service import TrustError, TrustService


class SettingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Literal["kill_switch", "auto_limit_paise", "window_days", "hard_cap_paise"]
    value: bool | int
    via: Literal["console", "whatsapp", "telegram", "voice", "test"] = "console"


def create_app(*, service: TrustService | None = None, api_key: str | None = None, seller_pin: str | None = None) -> FastAPI:
    cfg = settings()
    key = require(api_key or cfg.trust_api_key, "TRUST_API_KEY")
    pin = seller_pin or cfg.seller_console_pin

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owned: list = []
        if app.state.svc is None:
            pool = await create_pool(cfg.database_url_writer)
            store = StoreClient(cfg.store_url, require(cfg.store_writer_key, "STORE_WRITER_KEY"))
            app.state.svc = TrustService(pool, store, require(cfg.verdict_secret, "VERDICT_SECRET"),
                                         allow_ttl_s=cfg.allow_ttl_s, approved_ttl_s=cfg.approved_ttl_s,
                                         daily_write_cap=cfg.daily_write_cap, daily_refund_cap_paise=cfg.daily_refund_cap_paise)
            owned = [pool, store]
        yield
        for o in owned:
            await (o.aclose() if hasattr(o, "aclose") else o.close())

    app = FastAPI(title="Kavach trust service", version="1.0", lifespan=lifespan, docs_url="/docs" if cfg.env == "dev" else None, redoc_url=None)  # interactive docs only in dev
    app.state.svc = service

    def auth(x_api_key: str = Header(default="")) -> None:
        if not constant_time_equal(x_api_key, key):
            raise HTTPException(401, "missing or invalid API key")

    def svc() -> TrustService:
        return app.state.svc

    @app.exception_handler(TrustError)
    async def trust_error(_: Request, e: TrustError):
        return JSONResponse({"detail": e.detail}, status_code=e.status)

    @app.exception_handler(asyncpg.PostgresError)
    async def db_error(_: Request, e: asyncpg.PostgresError):
        return JSONResponse({"detail": "trust database error"}, status_code=500)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/verify", response_model=VerdictOut, dependencies=[Depends(auth)])
    async def verify(p: ProposalIn):
        return await svc().verify(p)

    @app.post("/approvals/{approval_id}/decide", response_model=VerdictOut, dependencies=[Depends(auth)])
    async def decide(approval_id: int, d: Decision):
        return await svc().decide(approval_id, d)

    @app.get("/approvals", dependencies=[Depends(auth)])
    async def approvals(status: Literal["pending", "approved", "rejected", "void"] = "pending"):
        rows = await svc().pool.fetch(
            """SELECT a.id, a.status, a.summary, a.created_at, p.tool, p.args, p.caller, v.reasons, v.results
               FROM approvals a JOIN proposals p ON p.id = a.proposal_id JOIN verdicts v ON v.proposal_id = a.proposal_id
               WHERE a.status = $1 ORDER BY a.created_at DESC LIMIT 50""", status)
        return [dict(r) for r in rows]

    @app.post("/execute", response_model=ExecuteOut, dependencies=[Depends(auth)])
    async def execute(req: ExecuteIn):
        return await svc().execute(req)

    @app.post("/settings", dependencies=[Depends(auth)])
    async def set_setting(body: SettingIn, x_seller_pin: str = Header(default="")):
        if not pin or not constant_time_equal(x_seller_pin, pin):
            raise HTTPException(403, "seller PIN required")
        return await svc().set_setting(body.name, body.value, body.via)

    @app.get("/audit/verify", dependencies=[Depends(auth)])
    async def audit_verify():
        broken = await svc().audit_verify()
        return {"intact": broken is None, "first_broken_row": broken}

    return app

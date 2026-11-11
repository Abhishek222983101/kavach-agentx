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
import secrets
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
from kavach.gateway import channels
from kavach.gateway import telegram as tg_routes
from kavach.gateway import whatsapp as wa_routes
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

    # Neon scales to zero after idle and drops connections: validate on checkout and recycle idle ones
    pool = AsyncConnectionPool(dsn, open=False, min_size=1, max_size=5, max_idle=60, check=AsyncConnectionPool.check_connection,
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
        st.seller_pin = pin
        st.bg_tasks = set()
        await channels.setup(app)
        from kavach.gateway import calls as calls_mod
        await calls_mod.setup(app)
        for hook in st.startup_hooks:          # tests can inject fakes after setup
            await hook(app)
        yield
        await channels.teardown(app)
        await st.bus.drain()
        for o in owned:
            await (o.aclose() if hasattr(o, "aclose") else o.close())

    app = FastAPI(title="Kavach API", version="1.0", lifespan=lifespan,
                  docs_url="/docs" if cfg.env == "dev" else None, redoc_url=None)
    app.state.pool, app.state.store, app.state.trust, app.state.checkpointer = pool, store, trust, checkpointer
    app.state.startup_hooks = []
    app.include_router(wa_routes.router)
    app.include_router(tg_routes.router)
    from kavach.gateway.calls import router as calls_router
    app.include_router(calls_router)
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
        return {"status": "ok", "llm_keys": counts, "channels": getattr(app.state, "channels_started", [])}

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
        rows = await app.state.pool.fetch(
            """SELECT o.id, o.item, o.category, o.status, o.paid_paise, o.refunded_paise, o.cod, o.perishable, o.note,
                      o.created_at, s.delivered_at, s.courier,
                      EXISTS (SELECT 1 FROM returns r WHERE r.order_id = o.id) AS has_return,
                      (SELECT count(*) FROM photos p WHERE p.order_id = o.id) AS photos
               FROM orders o LEFT JOIN shipments s ON s.awb = o.awb
               WHERE o.customer_id = $1 ORDER BY o.id""", conv["customer_id"])
        return {"customer_id": conv["customer_id"], "name": conv["name"], "orders": [dict(r) for r in rows]}

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

    @app.get("/api/seller/settings")
    async def seller_settings_get():
        """Public: the shop's current rules (kill switch, limits). Only changing them needs the PIN."""
        s = await app.state.store.settings()
        keep = ("kill_switch", "auto_limit_paise", "hard_cap_paise", "window_days", "freq_window_days")
        return {k: s.get(k) for k in keep}

    @app.get("/api/seller/calls")
    async def seller_calls():
        """Public status of phone alerts (number masked). Only the seller's own phone can ever be called."""
        calls = getattr(app.state, "calls", None)
        return await calls.view() if calls else {"enabled": False}

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

    # ───────────── B0 arena: the same message to a prompt-only agent (simulated, never moves money) ─────────────
    @app.post("/api/arena")
    async def arena(body: ChatIn, sess: str = Depends(session)):
        from kavach.agent import baseline
        text = clean(body.text)
        if not text:
            raise HTTPException(422, "empty message")
        conv = await web_conv(sess)
        if not app.state.caps.allow_user(f"web:{sess}"):
            return {"limited": True, "tries": 0, "paid_out_in": 0, "max_paid_rupees": 0, "runs": []}
        orders = await app.state.store.orders(conv["customer_id"], limit=10)

        async def view(o: dict) -> dict:
            ship = {}
            if o.get("awb"):
                try:
                    ship = await app.state.store.shipment(o["awb"])
                except Exception:  # noqa: BLE001 - the baseline just sees less
                    ship = {}
            return {"order_id": o["id"], "item": o["item"], "paid_rupees": o["paid_paise"] / 100,
                    "refunded_rupees": o["refunded_paise"] / 100, "status": o["status"], "cod": o["cod"],
                    "perishable": o["perishable"], "note": o["note"], "ordered_at": o["created_at"],
                    "delivered_at": ship.get("delivered_at")}

        views = await asyncio.gather(*[view(o) for o in orders])
        policy = [{"title": p["title"], "text": p["text"]} for p in await app.state.store.policies()]
        return await baseline.run(text, body.photo, list(views), policy, tries=3)

    # ───────────── public proof (no customer text, no phone numbers) ─────────────
    @app.get("/api/proof/audit")
    async def proof_audit(limit: int = 15):
        limit = max(1, min(limit, 50))
        rows = await app.state.pool.fetch(
            "SELECT i, ts, event, summary, prev_hash, hash FROM audit_log ORDER BY i DESC LIMIT $1", limit)
        total = await app.state.pool.fetchval("SELECT count(*) FROM audit_log")
        paid = await app.state.pool.fetchval(
            """SELECT p.trace_id FROM executions e JOIN proposals p ON p.id = e.proposal_id
               WHERE e.tool = 'issue_refund' ORDER BY e.ts DESC LIMIT 1""")
        blocked = await app.state.pool.fetchval(
            """SELECT p.trace_id FROM verdicts v JOIN proposals p ON p.id = v.proposal_id
               WHERE v.verdict = 'BLOCK' ORDER BY v.ts DESC LIMIT 1""")
        return {"total": total, "rows": [dict(r) for r in rows], "latest_paid_trace": paid, "latest_blocked_trace": blocked}

    @app.get("/api/proof/recent")
    async def proof_recent(limit: int = 14):
        rows = await app.state.pool.fetch(
            """SELECT p.trace_id, v.verdict, v.reasons, p.tool, v.ts,
                      (SELECT e.payload->>'channel' FROM events e WHERE e.trace_id = p.trace_id AND e.stage = 'ingest' LIMIT 1) AS channel
               FROM verdicts v JOIN proposals p ON p.id = v.proposal_id WHERE p.parent_id IS NULL
               ORDER BY v.ts DESC LIMIT $1""", max(1, min(limit, 50)))
        return [{**dict(r), "reasons": json.loads(r["reasons"]) if isinstance(r["reasons"], str) else r["reasons"]} for r in rows]

    _last_tamper = {"t": 0.0}

    @app.post("/api/proof/tamper")
    async def proof_tamper():
        """Copies the audit log into a temporary table, edits one row of the COPY, and runs the same
        audit_verify() on it. The real log is never touched (it is append-only by trigger anyway)."""
        if time.monotonic() - _last_tamper["t"] < 2:
            raise HTTPException(429, "one tamper test every 2 seconds")
        _last_tamper["t"] = time.monotonic()
        log: list[dict] = []

        async def step(conn, sql: str, *args, fetch: str = "val"):
            t = time.perf_counter()
            out = await (conn.fetchval(sql, *args) if fetch == "val" else conn.execute(sql, *args))
            log.append({"sql": sql.replace("$1", repr(args[0]) if args else "$1").replace("$2", repr(args[1]) if len(args) > 1 else "$2"),
                        "result": out if not isinstance(out, str) or fetch == "val" else out, "ms": round((time.perf_counter() - t) * 1000, 1)})
            return out

        async with app.state.pool.acquire() as conn:
            async with conn.transaction():
                await step(conn, "CREATE TEMP TABLE audit_copy ON COMMIT DROP AS SELECT * FROM audit_log", fetch="exec")
                n = await step(conn, "SELECT count(*) FROM audit_copy")
                if not n:
                    return {"rows": 0, "edited_row": None, "found_broken_row": None, "log": log}
                target = await conn.fetchrow(
                    "SELECT i, ts, event, summary, payload, prev_hash, hash FROM audit_copy ORDER BY i OFFSET $1 LIMIT 1", secrets.randbelow(n))
                before = await step(conn, "SELECT audit_verify('audit_copy')")
                edited = target["summary"].replace("BLOCK", "ALLOW", 1) if "BLOCK" in target["summary"] else target["summary"] + " (edited)"
                await step(conn, "UPDATE audit_copy SET summary = $1 WHERE i = $2", edited, target["i"], fetch="exec")
                recomputed = await conn.fetchval(
                    "SELECT audit_row_hash(prev_hash, ts, event, summary, payload) FROM audit_copy WHERE i = $1", target["i"])
                after = await step(conn, "SELECT audit_verify('audit_copy')")
        return {"rows": n, "edited_row": target["i"], "original": target["summary"], "edited": edited,
                "stored_hash": target["hash"], "recomputed_hash": recomputed,
                "broken_before": before, "found_broken_row": after, "log": log}

    @app.get("/api/proof/roles")
    async def proof_roles():
        """Asks Postgres itself what each service's database user may do."""
        checks = [("kavach_reader", "refunds", "INSERT"), ("kavach_reader", "orders", "UPDATE"),
                  ("kavach_reader", "executions", "INSERT"), ("kavach_reader", "settings", "UPDATE"),
                  ("kavach_reader", "audit_log", "UPDATE"), ("kavach_writer", "refunds", "INSERT"),
                  ("kavach_writer", "audit_log", "UPDATE"), ("kavach_writer", "audit_log", "DELETE")]
        out = []
        for role, table, priv in checks:
            ok = await app.state.pool.fetchval("SELECT has_table_privilege($1, $2, $3)", role, table, priv)
            out.append({"role": role, "table": table, "privilege": priv, "allowed": ok,
                        "sql": f"SELECT has_table_privilege('{role}', '{table}', '{priv}')"})
        # and a real attempt: the API's own connection tries to write a refund row inside a rolled-back transaction
        try:
            async with app.state.pool.acquire() as conn:
                tx = conn.transaction()
                await tx.start()
                try:
                    await conn.execute("INSERT INTO refunds(order_id, amount_paise, idempotency_key) VALUES (0, 1, 'proof')")
                    attempt = "succeeded (unexpected)"
                finally:
                    await tx.rollback()
        except Exception as e:  # noqa: BLE001 - the error IS the proof
            attempt = f"{type(e).__name__}: {str(e).splitlines()[0][:160]}"
        me = await app.state.pool.fetchval("SELECT current_user")
        trigger = await app.state.pool.fetchval(
            "SELECT count(*) FROM pg_trigger WHERE tgname = 'audit_no_update' AND NOT tgisinternal")
        return {"api_runs_as": me, "checks": out, "audit_append_only_trigger": bool(trigger),
                "write_attempt": {"sql": "INSERT INTO refunds(...) VALUES (...)", "as_role": me, "result": attempt}}

    @app.get("/api/proof/trace/{trace_id}")
    async def proof_trace(trace_id: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", trace_id):
            raise HTTPException(400, "bad trace id")
        from kavach.events import PUBLIC_KEYS
        rows = await app.state.pool.fetch(
            "SELECT stage, status, t_ms, payload, ts FROM events WHERE trace_id = $1 ORDER BY id LIMIT 60", trace_id)
        if not rows:
            raise HTTPException(404, "no decision with that reference")
        steps = []
        for r in rows:
            p = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"] or "{}")
            steps.append({"stage": r["stage"], "status": r["status"], "t_ms": r["t_ms"], "ts": r["ts"],
                          **{k: v for k, v in p.items() if k in PUBLIC_KEYS}})
        ex = await app.state.pool.fetchrow(
            """SELECT e.nonce, e.tool, e.amount_paise, e.result->>'status' AS status, e.ts, p.args_hash
               FROM executions e JOIN proposals p ON p.id = e.proposal_id WHERE p.trace_id = $1 LIMIT 1""", trace_id)
        return {"trace_id": trace_id, "steps": steps, "execution": dict(ex) if ex else None}

    return app

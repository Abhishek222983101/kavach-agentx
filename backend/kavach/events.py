"""Event bus for the live X-ray (ARCH §9.2).

Every agent step is (1) inserted into `events` for the trace page and evaluation, and (2) pushed to live
subscribers (Server-Sent Events). Subscribers filter by session or watch the global feed; the global feed
never carries message text or phone numbers, only stage, status, timings and verdicts.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import asyncpg

STAGES = ("ingest", "guard", "understand", "plan", "read", "propose", "verify", "route", "approve", "execute", "reply")
PUBLIC_KEYS = {"stage", "status", "t_ms", "trace_id", "verdict", "reasons", "tool", "intent", "plan", "guard_score",
               "guard_tags", "channel", "kind", "calls", "claims", "approval_id", "amount_paise", "source", "result", "decision"}


@dataclass(eq=False)  # identity-hashed: subscribers live in a set
class Subscriber:
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=500))
    session: str | None = None       # None = global feed (sanitised)


class EventBus:
    def __init__(self, pool: asyncpg.Pool | None):
        self.pool = pool
        self._subs: set[Subscriber] = set()
        self._trace_session: dict[str, str] = {}
        self.counters: dict[str, int] = defaultdict(int)
        self._pending: asyncio.Queue = asyncio.Queue(maxsize=10_000)
        self._writer: asyncio.Task | None = None

    def bind(self, trace_id: str, session: str) -> None:
        self._trace_session[trace_id] = session
        if len(self._trace_session) > 5000:   # bounded memory
            for k in list(self._trace_session)[:1000]:
                self._trace_session.pop(k, None)

    def viewers(self) -> int:
        return len(self._subs)

    def subscribe(self, session: str | None) -> Subscriber:
        s = Subscriber(session=session)
        self._subs.add(s)
        return s

    def unsubscribe(self, s: Subscriber) -> None:
        self._subs.discard(s)

    def _fanout(self, msg: dict, session: str | None) -> None:
        public = {k: v for k, v in msg.items() if k in PUBLIC_KEYS}
        for s in list(self._subs):
            payload = msg if (s.session is not None and s.session == session) else public if s.session is None else None
            if payload is None:
                continue
            try:
                s.queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # a slow viewer never blocks the agent

    async def emit(self, trace_id: str, stage: str, status: str, t0: float | None = None, **payload: Any) -> None:
        t_ms = int((time.perf_counter() - t0) * 1000) if t0 else None
        msg = {"type": "step", "trace_id": trace_id, "stage": stage, "status": status, "t_ms": t_ms, **payload}
        if stage == "route" and payload.get("verdict"):
            self.counters[payload["verdict"]] += 1
        self._fanout(msg, self._trace_session.get(trace_id))
        if self.pool is not None:
            # one background writer keeps DB order == emit order and never blocks the conversation
            if self._writer is None or self._writer.done():
                self._writer = asyncio.create_task(self._write_loop())
            try:
                self._pending.put_nowait((trace_id, stage, status, t_ms, json.loads(json.dumps(payload, default=str))))
            except asyncio.QueueFull:
                pass

    async def _write_loop(self) -> None:
        while True:
            row = await self._pending.get()
            try:
                await self.pool.execute("INSERT INTO events(trace_id, stage, status, t_ms, payload) VALUES ($1,$2,$3,$4,$5::jsonb)", *row)
            except Exception:  # noqa: BLE001 - observability must never break the conversation
                pass
            finally:
                self._pending.task_done()

    async def drain(self) -> None:
        """Wait until every queued event is written (tests, shutdown), then stop the writer."""
        if self._writer is not None and not self._writer.done():
            await self._pending.join()
            self._writer.cancel()
            self._writer = None

    def message(self, session: str | None, direction: str, text: str, trace_id: str | None = None) -> None:
        """A chat message for the session's own stream (never on the global feed)."""
        msg = {"type": "message", "direction": direction, "text": text, "trace_id": trace_id, "ts": time.time()}
        for s in list(self._subs):
            if s.session is not None and s.session == session:
                try:
                    s.queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass

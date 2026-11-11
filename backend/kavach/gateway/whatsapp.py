"""WhatsApp through the Twilio sandbox (ARCH §9.1, D-01, D-14).

Inbound: either a signed webhook (production) or polling Twilio's Messages API (local dev, no public URL).
Outbound: Twilio REST, spaced ≥ 3 s apart (sandbox limit), capped per day to protect the balance.
Facts verified against Twilio docs (11 Nov): sandbox sender whatsapp:+14155238886; users join with
"join <code>"; free-form replies only inside the 24-hour window; sessions expire 3 days after joining.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from twilio.request_validator import RequestValidator

from kavach.gateway import seller
from kavach.gateway.identity import TooManyNewCustomers, record_message, resolve

log = logging.getLogger("kavach.whatsapp")
API = "https://api.twilio.com/2010-04-01"
EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


class TwilioWhatsApp:
    def __init__(self, sid: str, token: str, sender: str, caps, *, transport: httpx.AsyncBaseTransport | None = None,
                 min_gap_s: float = 3.0):
        self.sid, self.sender, self.caps = sid, sender, caps
        self._c = httpx.AsyncClient(auth=(sid, token), timeout=15, transport=transport)
        self._lock = asyncio.Lock()
        self._last = 0.0
        self.min_gap_s = min_gap_s
        self.validator = RequestValidator(token)

    async def aclose(self) -> None:
        await self._c.aclose()

    async def send(self, to: str, text: str, buttons: list[tuple[str, str]] | None = None) -> None:
        if not self.caps.allow_whatsapp_out():
            log.warning("daily WhatsApp cap reached; message not sent")
            return
        to = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        async with self._lock:                                  # sandbox: one message every 3 seconds
            wait = self.min_gap_s - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            r = await self._c.post(f"{API}/Accounts/{self.sid}/Messages.json",
                                   data={"From": self.sender, "To": to, "Body": text[:1500]})
            self._last = time.monotonic()
        if r.status_code >= 400:
            code = r.json().get("code") if r.headers.get("content-type", "").startswith("application/json") else None
            raise RuntimeError(f"twilio {r.status_code} code={code}")   # 63015 = recipient hasn't joined the sandbox

    async def recent_inbound(self, since: datetime) -> list[dict]:
        """For polling mode: inbound messages to the sandbox number since `since` (oldest first)."""
        r = await self._c.get(f"{API}/Accounts/{self.sid}/Messages.json",
                              params={"To": self.sender, "DateSent>": since.strftime("%Y-%m-%d"), "PageSize": 50})
        r.raise_for_status()
        msgs = [m for m in r.json().get("messages", []) if m.get("direction") == "inbound"]
        out = []
        for m in msgs:
            sent = datetime.strptime(m["date_created"], "%a, %d %b %Y %H:%M:%S %z")
            if sent >= since:
                out.append({"MessageSid": m["sid"], "From": m["from"], "Body": m.get("body") or "",
                            "NumMedia": m.get("num_media") or "0", "ProfileName": "", "_at": sent})
        return [{k: v for k, v in x.items() if k != "_at"} for x in sorted(out, key=lambda x: x["_at"])]


def media_from(form: dict[str, Any]) -> list[dict]:
    out = []
    for i in range(min(int(form.get("NumMedia") or 0), 3)):
        ctype = form.get(f"MediaContentType{i}", "")
        kind = "image" if ctype.startswith("image/") else "audio" if ctype.startswith("audio/") else "file"
        out.append({"kind": kind, "content_type": ctype, "url": form.get(f"MediaUrl{i}", "")})
    return out


async def process_inbound(app, form: dict[str, Any]) -> None:
    """Handle one inbound WhatsApp message (webhook or poll). Safe to call twice for the same MessageSid."""
    try:
        await _process_inbound(app, form)
    except Exception as e:  # noqa: BLE001 - a customer must never be left in silence
        log.warning("whatsapp message failed: %s", type(e).__name__)
        frm = form.get("From", "")
        if frm.startswith("whatsapp:") and getattr(app.state, "whatsapp", None) is not None:
            try:
                await app.state.whatsapp.send(frm, "Maaf kijiye, hamari taraf se gadbad hui. Please dobara bhejiye. / Sorry, something went wrong on our side, please send it again.")
            except Exception:  # noqa: BLE001
                pass


async def _process_inbound(app, form: dict[str, Any]) -> None:
    st = app.state
    frm, body, sid = form.get("From", ""), (form.get("Body") or "").strip()[:1000], form.get("MessageSid", "")
    if not frm.startswith("whatsapp:") or not sid:
        return
    if body.lower().startswith("join "):          # the sandbox handles joins itself
        return
    seller_number = st.seller_whatsapp
    if seller_number and frm == f"whatsapp:{seller_number.removeprefix('whatsapp:')}":
        reply = await seller.handle(app, body, "whatsapp")
        if reply is not None:
            await st.whatsapp.send(frm, reply)
            return
    try:
        conv = await resolve(st.pool, st.trust, "whatsapp", frm.removeprefix("whatsapp:"), form.get("ProfileName") or None,
                             allow_new=st.caps.allow_new_customer)
    except TooManyNewCustomers:
        return
    media = media_from(form)
    if not await record_message(st.pool, conv, "in", body or "[media]", provider_msg_id=sid, media=media or None):
        return                                       # duplicate delivery: already handled
    if not st.caps.allow_user(f"whatsapp:{frm}"):
        await st.whatsapp.send(frm, "You've reached today's message limit for this demo. Please try again tomorrow.")
        return
    if any(m["kind"] == "audio" for m in media) and not body:
        await st.whatsapp.send(frm, "Voice notes coming soon. Please type your message for now 🙏")
        return
    await st.agent.handle(conv, body or "photo", media=media)


router = APIRouter()


@router.post("/webhooks/twilio/whatsapp")
async def webhook(request: Request) -> Response:
    app = request.app
    if getattr(app.state, "whatsapp", None) is None:
        raise HTTPException(404, "WhatsApp is not configured")
    form = dict(await request.form())
    url = app.state.public_base_url.rstrip("/") + "/webhooks/twilio/whatsapp"
    if not app.state.whatsapp.validator.validate(url, form, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "bad Twilio signature")
    task = asyncio.create_task(process_inbound(app, form))   # answer Twilio now; it times out after 15 s
    app.state.bg_tasks.add(task)
    task.add_done_callback(app.state.bg_tasks.discard)
    return Response(EMPTY_TWIML, media_type="application/xml")


async def poll_loop(app, interval_s: float = 3.0) -> None:
    """Local development: fetch new inbound messages from Twilio instead of receiving webhooks."""
    since = datetime.now(timezone.utc) - timedelta(seconds=5)
    seen: set[str] = set()
    while True:
        try:
            for m in await app.state.whatsapp.recent_inbound(since):
                if m["MessageSid"] in seen:
                    continue
                seen.add(m["MessageSid"])
                if len(seen) > 5000:            # bounded memory; the DB dedupes anyway
                    seen = set(list(seen)[-1000:])
                await process_inbound(app, m)
        except Exception as e:  # noqa: BLE001 - keep polling through transient errors
            log.warning("whatsapp poll error: %s", type(e).__name__)
        await asyncio.sleep(interval_s)

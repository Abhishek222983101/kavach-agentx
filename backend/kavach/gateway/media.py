"""Getting a customer's photo bytes for the photo check, per channel. Bytes are never stored anywhere.

- web: the browser uploads the image with the message; we keep it in memory for 10 minutes under its hash
  (the conversation state only holds the reference, so images never land in the database or checkpoints).
- WhatsApp: Twilio media URL, fetched with the account credentials.
- Telegram: file_id -> getFile -> download with the bot token.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import re
import time

from kavach.agent.vision import MAX_BYTES, sniff

log = logging.getLogger("kavach.media")
_MEM: dict[str, tuple[float, bytes]] = {}
TTL_S = 600
_DATA_URL = re.compile(r"^data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=\s]+)$")


def put_data_url(data_url: str) -> dict | None:
    """Validate a browser upload and keep it in memory. Returns a media entry, or None if it isn't a real image."""
    m = _DATA_URL.match(data_url or "")
    if not m:
        return None
    try:
        data = base64.b64decode(m.group(2), validate=False)
    except ValueError:
        return None
    if len(data) > MAX_BYTES or sniff(data) is None:
        return None
    digest = hashlib.sha256(data).hexdigest()
    now = time.time()
    for k in [k for k, (t, _) in _MEM.items() if now - t > TTL_S]:
        _MEM.pop(k, None)
    if len(_MEM) > 200:
        _MEM.clear()
    _MEM[digest] = (now, data)
    return {"kind": "image", "content_type": sniff(data), "sha256": digest, "ref": f"mem:{digest}"}


def fetcher(app):
    """Returns an async function media -> bytes | None, bound to this app's channel credentials."""
    async def fetch(media: dict) -> bytes | None:
        try:
            ref = media.get("ref") or ""
            if ref.startswith("mem:"):
                hit = _MEM.get(ref[4:])
                return hit[1] if hit else None
            if media.get("url") and getattr(app.state, "whatsapp", None) is not None:
                return await app.state.whatsapp.download(media["url"], MAX_BYTES)
            if media.get("tg_file_id") and getattr(app.state, "telegram", None) is not None:
                return await app.state.telegram.download(media["tg_file_id"], MAX_BYTES)
        except Exception as e:  # noqa: BLE001 - no bytes means "could not check", never a crash
            log.warning("could not fetch media: %s", type(e).__name__)
        return None
    return fetch

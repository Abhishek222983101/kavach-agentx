"""Signed verdict tokens (ARCH §9.5).

token = base64url(canonical(payload)) + "." + HMAC-SHA256(secret, that base64 text)
payload = {pid, tool, ah (args hash), v (ALLOW|APPROVED), exp (unix s), nonce}

The executor recomputes the args hash from the arguments it is *about to execute*; any change to the
action (₹500 -> ₹5,000, another order id) breaks the binding. Tokens expire and are single-use (the
nonce is a unique column in `executions`).
"""
from __future__ import annotations

import base64
import json
import secrets
import time
from dataclasses import dataclass

from kavach.common.canonical import canonical, constant_time_equal, hmac_hex


class TokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenPayload:
    pid: str
    tool: str
    ah: str
    v: str
    exp: int
    nonce: str


def mint(secret: str, *, pid: str, tool: str, ah: str, verdict: str, ttl_s: int, now: float | None = None) -> str:
    if verdict not in ("ALLOW", "APPROVED"):
        raise ValueError("only ALLOW or APPROVED verdicts get a token")
    payload = {"pid": pid, "tool": tool, "ah": ah, "v": verdict, "exp": int((now or time.time()) + ttl_s),
               "nonce": secrets.token_hex(12)}
    body = base64.urlsafe_b64encode(canonical(payload).encode()).decode().rstrip("=")
    return f"{body}.{hmac_hex(secret, body)}"


def verify(secret: str, token: str, *, now: float | None = None) -> TokenPayload:
    try:
        body, sig = token.split(".", 1)
    except ValueError as e:
        raise TokenError("malformed token") from e
    if not constant_time_equal(sig, hmac_hex(secret, body)):
        raise TokenError("bad signature")
    try:
        raw = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        p = TokenPayload(**raw)
    except Exception as e:  # noqa: BLE001 - any decoding problem is a bad token
        raise TokenError("unreadable token") from e
    if p.exp < (now or time.time()):
        raise TokenError("token expired")
    return p

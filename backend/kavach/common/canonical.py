"""Canonical JSON and hashing.

The verdict token binds to the *exact* action. Two dicts that mean the same thing must hash the same
(key order, whitespace), and anything that changes the meaning (an amount, an order id) must change
the hash. Floats are rejected: money is integer paise everywhere.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def _check(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("floats are not allowed in canonical data; use integer paise")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError("canonical dict keys must be strings")
            _check(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _check(v)


def canonical(value: Any) -> str:
    _check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def args_hash(tool: str, args: dict[str, Any]) -> str:
    return sha256_hex(canonical({"tool": tool, "args": args}))


def hmac_hex(secret: str, text: str) -> str:
    return hmac.new(secret.encode("utf-8"), text.encode("utf-8"), hashlib.sha256).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))

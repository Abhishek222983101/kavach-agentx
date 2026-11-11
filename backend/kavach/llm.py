"""Provider-agnostic text completion with automatic fallback.

Order: Gemini keys -> Groq keys -> Anthropic (if configured). A 429/5xx/timeout moves to the next
key/provider, so one exhausted key never takes the agent down. Tool-calling is layered on top later;
this module only guarantees "get me a completion from *something* that works".
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

load_dotenv()


class LLMUnavailable(Exception):
    """Every configured provider/key failed."""


@dataclass
class Provider:
    name: str
    key: str


def _keys(var: str) -> list[str]:
    return [k.strip() for k in os.getenv(var, "").split(",") if k.strip()]


_ENV = {"gemini": "GEMINI_API_KEYS", "groq": "GROQ_API_KEYS", "anthropic": "ANTHROPIC_API_KEY"}


def providers() -> list[Provider]:
    """Providers in LLM_ORDER (default: Groq first for latency, then Gemini, then Anthropic)."""
    order = [n.strip() for n in os.getenv("LLM_ORDER", "groq,gemini,anthropic").split(",") if n.strip() in _ENV]
    for n in _ENV:  # any provider missing from LLM_ORDER still goes last
        if n not in order:
            order.append(n)
    return [Provider(n, k) for n in order for k in _keys(_ENV[n])]


async def _call(client: httpx.AsyncClient, p: Provider, system: str, user: str, max_tokens: int, json_mode: bool) -> str:
    if p.name == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0,
                                 **({"responseMimeType": "application/json"} if json_mode else {})},
        }
        r = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                              params={"key": p.key}, json=body)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    if p.name == "groq":
        body = {"model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), "max_tokens": max_tokens, "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                **({"response_format": {"type": "json_object"}} if json_mode else {})}
        r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {p.key}"}, json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    if p.name == "anthropic":
        base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        body = {"model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5"), "max_tokens": max_tokens,
                "system": system, "messages": [{"role": "user", "content": user}]}
        r = await client.post(f"{base}/v1/messages", json=body,
                              headers={"x-api-key": p.key, "anthropic-version": "2023-06-01"})
        r.raise_for_status()
        return r.json()["content"][0]["text"]
    raise ValueError(p.name)


async def complete(system: str, user: str, *, max_tokens: int = 512, json_mode: bool = False,
                   client: httpx.AsyncClient | None = None) -> tuple[str, str]:
    """Return (text, provider_name). Raises LLMUnavailable if all providers fail."""
    own = client is None
    client = client or httpx.AsyncClient(timeout=30)
    errors: list[str] = []
    try:
        for p in providers():
            try:
                return await _call(client, p, system, user, max_tokens, json_mode), p.name
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
                errors.append(f"{p.name}: {type(e).__name__}")
        raise LLMUnavailable("; ".join(errors) or "no providers configured")
    finally:
        if own:
            await client.aclose()


async def complete_json(system: str, user: str, *, max_tokens: int = 700,
                        client: httpx.AsyncClient | None = None) -> tuple[dict, str]:
    """Like `complete`, but parses a JSON object. Tolerates ```json fences. Raises LLMUnavailable if no
    provider returns parseable JSON."""
    import json
    import re

    text, who = await complete(system, user, max_tokens=max_tokens, json_mode=True, client=client)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise LLMUnavailable(f"{who}: no JSON object in reply")
    try:
        return json.loads(m.group(0)), who
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"{who}: invalid JSON") from e

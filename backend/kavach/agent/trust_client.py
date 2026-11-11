"""The agent's only door to anything that changes state: the trust service (D-15)."""
from __future__ import annotations

from typing import Any

import httpx

from kavach.common.contracts import Decision, ExecuteIn, ExecuteOut, ProposalIn, VerdictOut


class TrustUnavailable(Exception):
    pass


class TrustClient:
    def __init__(self, base_url: str, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None, timeout: float = 15.0):
        self._c = httpx.AsyncClient(base_url=base_url, headers={"X-Api-Key": api_key}, timeout=timeout, transport=transport)

    async def aclose(self) -> None:
        await self._c.aclose()

    async def _post(self, path: str, body: dict, headers: dict | None = None) -> httpx.Response:
        try:
            return await self._c.post(path, json=body, headers=headers)
        except httpx.TransportError as e:
            raise TrustUnavailable(str(e)) from e

    async def verify(self, p: ProposalIn) -> VerdictOut:
        r = await self._post("/verify", p.model_dump(mode="json"))
        if r.status_code >= 500:
            raise TrustUnavailable(f"verify {r.status_code}")
        r.raise_for_status()
        return VerdictOut.model_validate(r.json())

    async def execute(self, req: ExecuteIn) -> ExecuteOut:
        r = await self._post("/execute", req.model_dump(mode="json"))
        if r.status_code >= 500:
            raise TrustUnavailable(f"execute {r.status_code}")
        r.raise_for_status()
        return ExecuteOut.model_validate(r.json())

    async def decide(self, approval_id: int, d: Decision) -> tuple[int, dict]:
        r = await self._post(f"/approvals/{approval_id}/decide", d.model_dump(mode="json"))
        return r.status_code, r.json()

    async def approvals(self, status: str = "pending") -> list[dict]:
        r = await self._c.get("/approvals", params={"status": status})
        r.raise_for_status()
        return r.json()

    async def provision(self, channel: str, channel_id: str, name: str | None) -> dict:
        r = await self._post("/demo/provision", {"channel": channel, "channel_id": channel_id, "name": name})
        r.raise_for_status()
        return r.json()

    async def set_setting(self, name: str, value: Any, pin: str, via: str) -> tuple[int, dict]:
        r = await self._post("/settings", {"name": name, "value": value, "via": via}, headers={"X-Seller-Pin": pin})
        return r.status_code, r.json()

    async def audit_verify(self) -> dict:
        r = await self._c.get("/audit/verify")
        r.raise_for_status()
        return r.json()

"""HTTP client for the Mock Store. Used by the agent (reader key) and the trust service (writer key).

Errors are explicit: NotFound for 404, StoreUnavailable for 5xx/timeouts (after retries), StoreRefused for
4xx business-rule refusals. Reads retry twice on 5xx/timeout (ARCH §14: courier 500 -> retry ×2 -> escalate).
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx


class StoreError(Exception):
    pass


class NotFound(StoreError):
    pass


class StoreUnavailable(StoreError):
    pass


class StoreRefused(StoreError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


class StoreClient:
    def __init__(self, base_url: str, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None,
                 timeout: float = 4.0, read_retries: int = 2):
        self._c = httpx.AsyncClient(base_url=base_url, headers={"X-Api-Key": api_key}, timeout=timeout, transport=transport)
        self._retries = read_retries
        self.calls: list[str] = []   # every call made, for the live X-ray / trace

    async def aclose(self) -> None:
        await self._c.aclose()

    async def _get(self, path: str, **params: Any) -> Any:
        last: Exception | None = None
        for attempt in range(self._retries + 1):
            self.calls.append(f"GET {path}")
            try:
                r = await self._c.get(path, params={k: v for k, v in params.items() if v is not None})
            except httpx.TransportError as e:
                last = e
            else:
                if r.status_code == 404:
                    raise NotFound(path)
                if r.status_code >= 500:
                    last = StoreUnavailable(f"{path}: {r.status_code}")
                elif r.status_code >= 400:
                    raise StoreRefused(r.status_code, r.json().get("detail", ""))
                else:
                    return r.json()
            if attempt < self._retries:
                await asyncio.sleep(0.15 * (attempt + 1))
        raise StoreUnavailable(str(last))

    async def _write(self, method: str, path: str, body: dict | None, idem: str) -> dict:
        self.calls.append(f"{method} {path}")
        try:
            r = await self._c.request(method, path, json=body, headers={"Idempotency-Key": idem})
        except httpx.TransportError as e:
            raise StoreUnavailable(str(e)) from e
        if r.status_code == 404:
            raise NotFound(path)
        if r.status_code >= 500:
            raise StoreUnavailable(f"{path}: {r.status_code}")
        if r.status_code >= 400:
            raise StoreRefused(r.status_code, r.json().get("detail", ""))
        return r.json()

    # reads
    async def customer(self, cid: str) -> dict: return await self._get(f"/customers/{cid}")
    async def customer_by_phone(self, phone: str) -> dict: return await self._get("/customers", phone=phone)
    async def order(self, oid: int) -> dict: return await self._get(f"/orders/{int(oid)}")
    async def orders(self, customer_id: str, limit: int = 10) -> list[dict]: return await self._get("/orders", customer_id=customer_id, limit=limit)
    async def shipment(self, awb: str) -> dict: return await self._get(f"/shipments/{awb}")
    async def refunds_for_order(self, oid: int) -> list[dict]: return await self._get("/refunds", order_id=int(oid))
    async def refunds_for_customer(self, cid: str, days: int = 30) -> list[dict]: return await self._get("/refunds", customer_id=cid, days=days)
    async def policies(self) -> list[dict]: return await self._get("/policies")
    async def photos(self, oid: int) -> list[dict]: return await self._get("/photos", order_id=int(oid))
    async def settings(self) -> dict: return await self._get("/settings")

    # writes (writer key only; the store refuses them otherwise)
    async def create_refund(self, order_id: int, amount_paise: int, idem: str) -> dict:
        return await self._write("POST", "/refunds", {"order_id": order_id, "amount_paise": amount_paise}, idem)

    async def create_return(self, order_id: int, reason: str, idem: str) -> dict:
        return await self._write("POST", "/returns", {"order_id": order_id, "reason": reason}, idem)

    async def update_address(self, order_id: int, new_address: str, idem: str) -> dict:
        return await self._write("PATCH", f"/orders/{int(order_id)}/address", {"new_address": new_address}, idem)

    async def cancel_order(self, order_id: int, idem: str) -> dict:
        return await self._write("POST", f"/orders/{int(order_id)}/cancel", None, idem)

    async def set_setting(self, name: str, value: bool | int) -> dict:
        self.calls.append(f"PUT /settings/{name}")
        r = await self._c.put(f"/settings/{name}", json={"value": value})
        if r.status_code >= 400:
            raise StoreRefused(r.status_code, r.json().get("detail", ""))
        return r.json()

    async def chaos(self, **kw: Any) -> dict:
        r = await self._c.post("/admin/chaos", json=kw)
        if r.status_code >= 400:
            raise StoreRefused(r.status_code, r.json().get("detail", ""))
        return r.json()

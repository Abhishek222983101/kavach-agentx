"""Phase 1 acceptance: the Mock Store API (real HTTP semantics via ASGI, real Postgres)."""
import httpx
import pytest

from kavach.db.seed import load
from kavach.store.app import create_app
from kavach.store.client import NotFound, StoreClient, StoreRefused, StoreUnavailable

RK, WK = "reader-key-0123456789", "writer-key-0123456789"


@pytest.fixture(scope="session")
async def seeded(pools):
    async with pools["owner"].acquire() as c:
        return await load(c)


@pytest.fixture(scope="session")
def store_app(pools, seeded):
    return create_app(reader_pool=pools["reader"], writer_pool=pools["writer"], reader_key=RK, writer_key=WK)


@pytest.fixture
async def clients(store_app):
    t = httpx.ASGITransport(app=store_app)
    r, w = StoreClient("http://store", RK, transport=t), StoreClient("http://store", WK, transport=t)
    yield r, w
    await w.chaos()  # reset chaos after each test
    await r.aclose(); await w.aclose()


async def test_seed_has_scenarios(seeded, clients):
    r, _ = clients
    assert seeded["orders"] >= 50
    o = await r.order(1042)
    assert (o["customer_id"], o["paid_paise"], o["status"]) == ("c01", 129900, "delivered")
    assert "ignore all previous rules" in (await r.order(1049))["note"]
    assert len(await r.policies()) == 8
    s = await r.settings()
    assert s["auto_limit_paise"] == 50000 and s["window_days"] == 7 and s["kill_switch"] is False


async def test_auth_required_and_reader_cannot_write(store_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=store_app), base_url="http://s") as c:
        assert (await c.get("/orders/1042")).status_code == 401
        assert (await c.get("/orders/1042", headers={"X-Api-Key": "wrong"})).status_code == 401
        h = {"X-Api-Key": RK, "Idempotency-Key": "abcdefgh1"}
        assert (await c.post("/refunds", json={"order_id": 1043, "amount_paise": 100}, headers=h)).status_code == 403
        assert (await c.post("/admin/chaos", json={"courier_down": True}, headers=h)).status_code == 403
        assert (await c.put("/settings/kill_switch", json={"value": True}, headers=h)).status_code == 403


async def test_validation_and_injection_safe(store_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=store_app), base_url="http://s") as c:
        h = {"X-Api-Key": WK}
        assert (await c.get("/orders/1042 OR 1=1", headers=h)).status_code == 422
        assert (await c.get("/orders", params={"customer_id": "c01' OR '1'='1"}, headers=h)).json() == []
        bad = await c.post("/refunds", json={"order_id": 1043, "amount_paise": 100, "extra": 1}, headers={**h, "Idempotency-Key": "abcdefgh2"})
        assert bad.status_code == 422
        assert (await c.post("/refunds", json={"order_id": 1043, "amount_paise": 100}, headers=h)).status_code == 400  # no idem key


async def test_refund_is_idempotent_and_bounded(clients, pools):
    _, w = clients
    first = await w.create_refund(1043, 10000, "test-idem-1043")
    again = await w.create_refund(1043, 10000, "test-idem-1043")
    assert first["id"] == again["id"] and again["replayed"] is True
    rows = await pools["owner"].fetchval("SELECT count(*) FROM refunds WHERE idempotency_key = 'test-idem-1043'")
    assert rows == 1
    with pytest.raises(StoreRefused) as e:
        await w.create_refund(1043, 99999, "test-idem-1043")   # same key, different content
    assert e.value.status == 409
    with pytest.raises(StoreRefused) as e:
        await w.create_refund(1050, 100, "test-over-1050")      # already fully refunded
    assert e.value.status == 422


async def test_pre_dispatch_rules(clients):
    _, w = clients
    with pytest.raises(StoreRefused):
        await w.update_address(1042, "New address, Pune 411001", "idem-addr-1042")   # delivered
    ok = await w.update_address(1046, "Flat 3, Lake View, Powai, Mumbai 400076", "idem-addr-1046")
    assert ok["address"].startswith("Flat 3")
    with pytest.raises(StoreRefused):
        await w.create_return(1048, "damaged", "idem-ret-1048")   # perishable


async def test_chaos_courier_down_retries_then_unavailable(clients):
    r, w = clients
    awb = (await r.order(1047))["awb"]
    assert (await r.shipment(awb))["status"] == "in_transit"
    await w.chaos(courier_down=True)
    r.calls.clear()
    with pytest.raises(StoreUnavailable):
        await r.shipment(awb)
    assert r.calls.count(f"GET /shipments/{awb}") == 3      # first try + 2 retries
    with pytest.raises(NotFound):
        await r.order(999999)


async def test_auth_is_checked_before_anything_else(store_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=store_app), base_url="http://s") as c:
        assert (await c.post("/refunds", json={"order_id": 1043, "amount_paise": 1})).status_code == 401

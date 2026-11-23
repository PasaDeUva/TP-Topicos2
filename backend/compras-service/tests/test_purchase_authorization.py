import uuid

from fastapi import HTTPException

from app.identity import current_customer
from app.main import app
from tests.conftest import TEST_CUSTOMER_ID, evento_fake


async def test_customer_owns_derived_purchase_and_reads(client, eventos_simulados):
    event_id, event = evento_fake()
    eventos_simulados["eventos"][event_id] = event
    body = {"evento_id": event_id, "modalidad_id": event["modalidades"][0]["id"]}
    headers = {"Idempotency-Key": "key"}
    created = await client.post("/compras", json=body, headers=headers)
    assert created.status_code == 201
    assert created.json()["cliente_id"] == str(TEST_CUSTOMER_ID)
    assert (await client.get("/compras")).json()[0]["id"] == created.json()["id"]
    other = uuid.uuid4()
    assert (
        await client.get("/compras", params={"cliente_id": str(other)})
    ).status_code == 403
    body["cliente_id"] = str(other)
    assert (
        await client.post("/compras", json=body, headers=headers)
    ).status_code == 403
    app.dependency_overrides[current_customer] = lambda: other
    assert (await client.get(f"/compras/{created.json()['id']}")).status_code == 404
    assert (await client.get("/compras")).json() == []


async def test_retries_reauthorize_before_lookup(client, eventos_simulados):
    event_id, event = evento_fake()
    eventos_simulados["eventos"][event_id] = event
    body = {"evento_id": event_id, "modalidad_id": event["modalidades"][0]["id"]}
    headers = {"Idempotency-Key": "key"}
    assert (
        await client.post("/compras", json=body, headers=headers)
    ).status_code == 201

    def unavailable():
        raise HTTPException(status_code=503, detail="identity unavailable")

    app.dependency_overrides[current_customer] = unavailable
    assert (
        await client.post("/compras", json=body, headers=headers)
    ).status_code == 503


async def test_anonymous_purchases_are_rejected(client):
    del app.dependency_overrides[current_customer]
    assert (await client.get("/compras")).status_code == 401


async def test_same_idempotency_key_is_scoped_to_customer(client, eventos_simulados):
    event_id, event = evento_fake()
    eventos_simulados["eventos"][event_id] = event
    body = {"evento_id": event_id, "modalidad_id": event["modalidades"][0]["id"]}
    headers = {"Idempotency-Key": "same-key"}
    first = await client.post("/compras", json=body, headers=headers)
    other = uuid.uuid4()
    app.dependency_overrides[current_customer] = lambda: other
    second = await client.post("/compras", json=body, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert second.json()["cliente_id"] == str(other)

import uuid

from app.identity import current_organizer
from app.main import app
from tests.conftest import TEST_OWNER_ID, evento_payload


async def test_creation_uses_authenticated_owner(client):
    payload = evento_payload()
    del payload["owner_id"]
    response = await client.post("/eventos", json=payload)
    assert response.status_code == 201
    assert response.json()["owner_id"] == str(TEST_OWNER_ID)


async def test_owner_can_edit_without_supplying_owner_id(client):
    created = await client.post("/eventos", json=evento_payload())
    event_id = created.json()["id"]
    payload = evento_payload(nombre="Updated")
    del payload["owner_id"]
    response = await client.put(f"/eventos/{event_id}", json=payload)
    assert response.status_code == 200
    assert response.json()["owner_id"] == str(TEST_OWNER_ID)
    assert response.json()["nombre"] == "Updated"


async def test_supplied_different_owner_cannot_create_or_transfer(client):
    created = await client.post("/eventos", json=evento_payload())
    event_id = created.json()["id"]
    payload = evento_payload(owner_id=str(uuid.uuid4()), nombre="Changed")
    assert (await client.post("/eventos", json=payload)).status_code == 403
    assert (await client.put(f"/eventos/{event_id}", json=payload)).status_code == 403
    assert (await client.get(f"/eventos/{event_id}")).json()["nombre"] != "Changed"


async def test_other_owner_cannot_modify_or_delete(client):
    created = await client.post("/eventos", json=evento_payload())
    event_id = created.json()["id"]
    app.dependency_overrides[current_organizer] = uuid.uuid4
    payload = evento_payload()
    del payload["owner_id"]
    assert (await client.put(f"/eventos/{event_id}", json=payload)).status_code == 404
    assert (await client.delete(f"/eventos/{event_id}")).status_code == 404
    assert (await client.get(f"/eventos/{event_id}")).json()["activo"] is True


async def test_missing_credentials_rejected_but_catalog_public(client):
    del app.dependency_overrides[current_organizer]
    assert (await client.post("/eventos", json=evento_payload())).status_code == 401
    assert (await client.get("/eventos")).status_code == 200

import uuid

from httpx import AsyncClient

from tests.conftest import evento_payload

# ---------------------------------------------------------------------------
# POST /eventos — Alta
# ---------------------------------------------------------------------------


async def test_crear_evento_success(client: AsyncClient):
    payload = evento_payload()

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == payload["nombre"]
    assert data["activo"] is True
    assert len(data["modalidades"]) == 1
    assert data["modalidades"][0]["tipo"] == "general"
    assert uuid.UUID(data["id"])


async def test_crear_evento_failsWhenNombreFaltante(client: AsyncClient):
    payload = evento_payload()
    del payload["nombre"]

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_crear_evento_failsWhenTipoInvalido(client: AsyncClient):
    payload = evento_payload(modalidades=[{"nombre": "VIP", "tipo": "invalido"}])

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


# ---------------------------------------------------------------------------
# GET /eventos — Listado
# ---------------------------------------------------------------------------


async def test_listar_eventos_success(client: AsyncClient):
    await client.post("/eventos", json=evento_payload(nombre="Evento A"))
    await client.post("/eventos", json=evento_payload(nombre="Evento B"))

    response = await client.get("/eventos")

    assert response.status_code == 200
    nombres = [e["nombre"] for e in response.json()]
    assert "Evento A" in nombres
    assert "Evento B" in nombres


async def test_listar_eventos_incluyeInactivos(client: AsyncClient):
    # Crea un evento y lo da de baja
    r = await client.post("/eventos", json=evento_payload(nombre="Para Baja"))
    evento_id = r.json()["id"]
    await client.delete(f"/eventos/{evento_id}")

    response = await client.get("/eventos")

    assert response.status_code == 200
    todos = {e["id"]: e for e in response.json()}
    assert evento_id in todos
    assert todos[evento_id]["activo"] is False


# ---------------------------------------------------------------------------
# GET /eventos/{id} — Detalle
# ---------------------------------------------------------------------------


async def test_obtener_evento_success(client: AsyncClient):
    r = await client.post("/eventos", json=evento_payload())
    evento_id = r.json()["id"]

    response = await client.get(f"/eventos/{evento_id}")

    assert response.status_code == 200
    assert response.json()["id"] == evento_id
    assert len(response.json()["modalidades"]) == 1


async def test_obtener_evento_failsWhenNoExiste(client: AsyncClient):
    response = await client.get(f"/eventos/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /eventos/{id} — Edición completa
# ---------------------------------------------------------------------------


async def test_editar_evento_success(client: AsyncClient):
    r = await client.post(
        "/eventos",
        json=evento_payload(
            nombre="Original",
            modalidades=[{"nombre": "Campo", "tipo": "general"}],
        ),
    )
    evento_id = r.json()["id"]

    nuevo_payload = evento_payload(
        nombre="Actualizado",
        modalidades=[
            {"nombre": "Platea", "tipo": "numerado"},
            {"nombre": "VIP", "tipo": "numerado"},
        ],
    )
    response = await client.put(f"/eventos/{evento_id}", json=nuevo_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Actualizado"
    # Las modalidades anteriores se reemplazaron
    assert len(data["modalidades"]) == 2
    tipos = {m["tipo"] for m in data["modalidades"]}
    assert tipos == {"numerado"}


async def test_editar_evento_failsWhenNoExiste(client: AsyncClient):
    response = await client.put(f"/eventos/{uuid.uuid4()}", json=evento_payload())

    assert response.status_code == 404


async def test_editar_evento_failsWhenNombreFaltante(client: AsyncClient):
    r = await client.post("/eventos", json=evento_payload())
    evento_id = r.json()["id"]

    payload = evento_payload()
    del payload["nombre"]
    response = await client.put(f"/eventos/{evento_id}", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


# ---------------------------------------------------------------------------
# DELETE /eventos/{id} — Baja lógica
# ---------------------------------------------------------------------------


async def test_eliminar_evento_success(client: AsyncClient):
    r = await client.post("/eventos", json=evento_payload())
    evento_id = r.json()["id"]

    response = await client.delete(f"/eventos/{evento_id}")

    assert response.status_code == 200
    assert response.json()["activo"] is False
    # Verificar que el registro sigue en la DB
    get_resp = await client.get(f"/eventos/{evento_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["activo"] is False


async def test_eliminar_evento_failsWhenNoExiste(client: AsyncClient):
    response = await client.delete(f"/eventos/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Bitácora HTTP
# ---------------------------------------------------------------------------


async def test_bitacora_propagaCorrelationId(client: AsyncClient):
    correlation_id = str(uuid.uuid4())

    response = await client.get(
        "/eventos", headers={"X-Correlation-Id": correlation_id}
    )

    assert response.status_code == 200
    assert response.headers.get("x-correlation-id") == correlation_id

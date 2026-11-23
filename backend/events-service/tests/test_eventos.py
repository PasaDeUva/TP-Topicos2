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


async def test_crear_evento_failsWhenNombreVacio(client: AsyncClient):
    payload = evento_payload(nombre="")

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_crear_evento_failsWhenNombreDemasiadoLargo(client: AsyncClient):
    payload = evento_payload(nombre="A" * 256)

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_crear_evento_failsWhenTipoInvalido(client: AsyncClient):
    payload = evento_payload(modalidades=[{"nombre": "VIP", "tipo": "invalido"}])

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_crear_evento_failsWhenSinModalidades(client: AsyncClient):
    payload = evento_payload(modalidades=[])

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_crear_evento_failsWhenModalidadNombreDemasiadoLargo(
    client: AsyncClient,
):
    payload = evento_payload(
        modalidades=[
            {"nombre": "M" * 101, "tipo": "general", "precio": "100.00", "cupo": 10}
        ]
    )

    response = await client.post("/eventos", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_crear_evento_failsWhenFechaSinTimezone(client: AsyncClient):
    payload = evento_payload(fecha="2027-03-20T18:00:00")

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


async def test_listar_eventos_ordenDeterminista(client: AsyncClient):
    await client.post("/eventos", json=evento_payload(nombre="Primero"))
    await client.post("/eventos", json=evento_payload(nombre="Segundo"))

    response = await client.get("/eventos")

    assert response.status_code == 200
    eventos = response.json()
    assert len(eventos) >= 2
    for i in range(len(eventos) - 1):
        assert eventos[i]["creado_en"] <= eventos[i + 1]["creado_en"]


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


async def test_obtener_evento_failsWhenUUIDInvalido(client: AsyncClient):
    response = await client.get("/eventos/no-es-un-uuid")

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid path parameter"}


# ---------------------------------------------------------------------------
# PUT /eventos/{id} — Edición completa
# ---------------------------------------------------------------------------


async def test_editar_evento_success(client: AsyncClient):
    r = await client.post(
        "/eventos",
        json=evento_payload(
            nombre="Original",
            modalidades=[
                {
                    "nombre": "Campo",
                    "tipo": "general",
                    "precio": "1500.00",
                    "cupo": 50,
                }
            ],
        ),
    )
    evento_id = r.json()["id"]

    nuevo_payload = evento_payload(
        nombre="Actualizado",
        modalidades=[
            {
                "nombre": "Platea",
                "tipo": "numerado",
                "sectores": [
                    {
                        "nombre": "Sector A",
                        "precio": "2500.00",
                        "asientos": [
                            {"fila": "1", "numero": 1},
                            {"fila": "1", "numero": 2},
                        ],
                    }
                ],
            },
        ],
    )
    response = await client.put(f"/eventos/{evento_id}", json=nuevo_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Actualizado"
    assert len(data["modalidades"]) == 1
    assert data["modalidades"][0]["tipo"] == "numerado"
    assert len(data["modalidades"][0]["sectores"]) == 1
    assert len(data["modalidades"][0]["sectores"][0]["asientos"]) == 2


async def test_editar_evento_preservaModalidadPorId(client: AsyncClient):
    r = await client.post(
        "/eventos",
        json=evento_payload(
            nombre="Original",
            modalidades=[
                {
                    "nombre": "Campo",
                    "tipo": "general",
                    "precio": "1000.00",
                    "cupo": 20,
                }
            ],
        ),
    )
    evento_id = r.json()["id"]
    modalidad_id = r.json()["modalidades"][0]["id"]

    nuevo_payload = evento_payload(
        nombre="Editado",
        modalidades=[
            {
                "id": modalidad_id,
                "nombre": "Campo VIP",
                "tipo": "general",
                "precio": "1200.00",
                "cupo": 25,
            }
        ],
    )
    response = await client.put(f"/eventos/{evento_id}", json=nuevo_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["modalidades"][0]["id"] == modalidad_id
    assert data["modalidades"][0]["nombre"] == "Campo VIP"
    assert float(data["modalidades"][0]["precio"]) == 1200.00
    assert data["modalidades"][0]["cupo"] == 25


async def test_editar_evento_failsWhenModalidadOmitidaTieneReservas(
    client: AsyncClient,
):
    r = await client.post(
        "/eventos",
        json=evento_payload(
            modalidades=[
                {
                    "nombre": "General",
                    "tipo": "general",
                    "precio": "500.00",
                    "cupo": 10,
                }
            ]
        ),
    )
    evento_id = r.json()["id"]
    modalidad_id = r.json()["modalidades"][0]["id"]

    # Crear una reserva en esa modalidad
    r_res = await client.post(
        f"/eventos/{evento_id}/modalidades/{modalidad_id}/reservas"
    )
    assert r_res.status_code == 201

    # Intentar editar el evento omitiendo la modalidad con reservas
    nuevo_payload = evento_payload(
        modalidades=[
            {
                "nombre": "Nueva General",
                "tipo": "general",
                "precio": "600.00",
                "cupo": 15,
            }
        ]
    )
    response = await client.put(f"/eventos/{evento_id}", json=nuevo_payload)
    assert response.status_code == 409
    assert "reservas" in response.json()["detail"]


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


async def test_bitacora_registraError500(client: AsyncClient, capsys):
    correlation_id = str(uuid.uuid4())

    async def _failing_get_session():
        raise RuntimeError("database connection failed")
        yield

    from app.database import get_session
    from app.main import app

    app.dependency_overrides[get_session] = _failing_get_session

    try:
        response = await client.get(
            "/eventos", headers={"X-Correlation-Id": correlation_id}
        )
        assert response.status_code == 500
        assert response.headers.get("x-correlation-id") == correlation_id
        assert response.json() == {"detail": "internal server error"}

        captured = capsys.readouterr()
        assert correlation_id in captured.out
        assert '"status_code": 500' in captured.out
    finally:
        app.dependency_overrides.clear()


def test_config_reserva_ttl_minutes_default():
    from app.config import Settings

    cfg = Settings()
    assert cfg.reserva_ttl_minutes == 10


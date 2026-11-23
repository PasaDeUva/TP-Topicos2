import asyncio
import uuid

from sqlalchemy import text

from app.identity import current_customer
from app.main import app
from tests.conftest import TEST_CUSTOMER_ID, evento_fake

CLIENTE_ID = str(TEST_CUSTOMER_ID)


def compra_payload(evento_id: str, modalidad_id: str, cliente_id: str = CLIENTE_ID):
    return {
        "cliente_id": cliente_id,
        "evento_id": evento_id,
        "modalidad_id": modalidad_id,
    }


async def registrar(client, body: dict, key: str = "clave-1", correlation=None):
    headers = {"Idempotency-Key": key}
    if correlation:
        headers["X-Correlation-Id"] = correlation
    return await client.post("/compras", json=body, headers=headers)


async def test_registro_exitoso_devuelve_201(client, eventos_simulados):
    evento_id, evento = evento_fake()
    modalidad_id = evento["modalidades"][0]["id"]
    eventos_simulados["eventos"][evento_id] = evento

    response = await registrar(client, compra_payload(evento_id, modalidad_id))

    assert response.status_code == 201
    datos = response.json()
    assert datos["evento_id"] == evento_id
    assert datos["modalidad_id"] == modalidad_id
    assert "idempotency_key" not in datos
    assert "creado_en" in datos


async def test_evento_inexistente_devuelve_404(client, eventos_simulados):
    evento_id, _ = evento_fake()
    response = await registrar(client, compra_payload(evento_id, str(uuid.uuid4())))
    assert response.status_code == 404


async def test_modalidad_ajena_al_evento_devuelve_404(client, eventos_simulados):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento
    response = await registrar(client, compra_payload(evento_id, str(uuid.uuid4())))
    assert response.status_code == 404


async def test_evento_inactivo_devuelve_409(client, eventos_simulados):
    evento_id, evento = evento_fake(activo=False)
    eventos_simulados["eventos"][evento_id] = evento
    modalidad_id = evento["modalidades"][0]["id"]

    response = await registrar(client, compra_payload(evento_id, modalidad_id))

    assert response.status_code == 409
    assert response.json() == {"detail": "evento inactivo"}


async def test_modalidad_numerada_devuelve_409(client, eventos_simulados):
    modalidad = {"id": str(uuid.uuid4()), "nombre": "Platea", "tipo": "numerado"}
    evento_id, evento = evento_fake(modalidades=[modalidad])
    eventos_simulados["eventos"][evento_id] = evento

    response = await registrar(client, compra_payload(evento_id, modalidad["id"]))

    assert response.status_code == 409
    assert response.json() == {"detail": "modalidad no disponible"}


async def test_eventos_caido_devuelve_503_y_no_registra(
    client, eventos_simulados, session_factory
):
    evento_id, evento = evento_fake()
    eventos_simulados["modo"] = "caido"

    response = await registrar(
        client, compra_payload(evento_id, evento["modalidades"][0]["id"])
    )

    assert response.status_code == 503
    async with session_factory() as s:
        total = (await s.execute(text("SELECT count(*) FROM compras"))).scalar()
    assert total == 0


async def test_eventos_con_5xx_devuelve_503(client, eventos_simulados):
    evento_id, evento = evento_fake()
    eventos_simulados["modo"] = "5xx"

    response = await registrar(
        client, compra_payload(evento_id, evento["modalidades"][0]["id"])
    )

    assert response.status_code == 503


async def test_body_invalido_devuelve_400(client):
    response = await registrar(client, {"cliente_id": "no-uuid", "evento_id": "x"})
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_clave_ausente_devuelve_400(client):
    body = compra_payload(str(uuid.uuid4()), str(uuid.uuid4()))
    response = await client.post("/compras", json=body)
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid body"}


async def test_reintento_identico_devuelve_200_sin_consultar_eventos(
    client, eventos_simulados
):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento
    body = compra_payload(evento_id, evento["modalidades"][0]["id"])

    primera = await registrar(client, body)
    llamadas = eventos_simulados["llamadas"]
    segunda = await registrar(client, body)

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primera.json()["id"]
    assert eventos_simulados["llamadas"] == llamadas


async def test_clave_con_contenido_distinto_devuelve_409(client, eventos_simulados):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento
    modalidad_id = evento["modalidades"][0]["id"]
    await registrar(client, compra_payload(evento_id, modalidad_id))

    otro_evento_id, otro = evento_fake()
    eventos_simulados["eventos"][otro_evento_id] = otro
    response = await registrar(
        client, compra_payload(otro_evento_id, otro["modalidades"][0]["id"])
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "idempotency conflict"}


async def test_solicitudes_concurrentes_dejan_una_sola_compra(
    client, eventos_simulados, session_factory
):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento
    body = compra_payload(evento_id, evento["modalidades"][0]["id"])

    respuestas = await asyncio.gather(registrar(client, body), registrar(client, body))

    assert sorted(r.status_code for r in respuestas) == [200, 201]
    assert respuestas[0].json()["id"] == respuestas[1].json()["id"]
    async with session_factory() as s:
        total = (await s.execute(text("SELECT count(*) FROM compras"))).scalar()
    assert total == 1


async def test_detalle_de_compra(client, eventos_simulados):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento
    creada = await registrar(
        client, compra_payload(evento_id, evento["modalidades"][0]["id"])
    )

    response = await client.get(f"/compras/{creada.json()['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == creada.json()["id"]


async def test_detalle_inexistente_devuelve_404_y_uuid_invalido_400(client):
    assert (await client.get(f"/compras/{uuid.uuid4()}")).status_code == 404
    response = await client.get("/compras/no-uuid")
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid path parameter"}


async def test_listado_filtra_por_cliente_y_ordena_descendente(
    client, eventos_simulados
):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento
    modalidad_id = evento["modalidades"][0]["id"]
    otro_cliente = str(uuid.uuid4())

    primera = await registrar(client, compra_payload(evento_id, modalidad_id), "k1")
    segunda = await registrar(client, compra_payload(evento_id, modalidad_id), "k2")
    app.dependency_overrides[current_customer] = lambda: uuid.UUID(otro_cliente)
    await registrar(client, compra_payload(evento_id, modalidad_id, otro_cliente), "k3")
    app.dependency_overrides[current_customer] = lambda: TEST_CUSTOMER_ID

    response = await client.get("/compras", params={"cliente_id": CLIENTE_ID})

    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert ids == [segunda.json()["id"], primera.json()["id"]]


async def test_listado_sin_cliente_valido_devuelve_400(client):
    assert (await client.get("/compras")).status_code == 200
    assert (await client.get("/compras", params={"cliente_id": "x"})).status_code == 400


async def test_correlation_id_se_propaga_a_eventos(client, eventos_simulados):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento
    correlation = str(uuid.uuid4())

    response = await registrar(
        client,
        compra_payload(evento_id, evento["modalidades"][0]["id"]),
        correlation=correlation,
    )

    assert response.headers["X-Correlation-Id"] == correlation
    assert eventos_simulados["correlation_ids"] == [correlation]


async def test_correlation_id_generado_se_propaga_a_eventos_si_no_se_envia_header(
    client, eventos_simulados
):
    evento_id, evento = evento_fake()
    eventos_simulados["eventos"][evento_id] = evento

    response = await registrar(
        client,
        compra_payload(evento_id, evento["modalidades"][0]["id"]),
    )

    assert response.status_code == 201
    correlation_generado = response.headers["X-Correlation-Id"]
    assert correlation_generado is not None
    assert eventos_simulados["correlation_ids"] == [correlation_generado]

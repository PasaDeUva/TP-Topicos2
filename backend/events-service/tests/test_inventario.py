from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from httpx import AsyncClient
import pytest

from tests.conftest import evento_payload


@pytest.fixture
def evento_con_inventario_payload():
    return evento_payload(
        nombre="Concierto Rock",
        modalidades=[
            {
                "nombre": "Campo General",
                "tipo": "general",
                "precio": "5000.00",
                "cupo": 2,
            },
            {
                "nombre": "Platea Baja",
                "tipo": "numerado",
                "sectores": [
                    {
                        "nombre": "Sector A",
                        "precio": "8000.00",
                        "asientos": [
                            {"fila": "1", "numero": 1},
                            {"fila": "1", "numero": 2},
                        ],
                    }
                ],
            },
        ],
    )


async def test_obtener_disponibilidad_general_y_numerada(
    client: AsyncClient, evento_con_inventario_payload
):
    r = await client.post("/eventos", json=evento_con_inventario_payload)
    assert r.status_code == 201
    evento = r.json()
    general_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "general")
    numerada_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "numerado")

    # Disponibilidad general inicial = cupo (2)
    resp_gen = await client.get(f"/eventos/{evento['id']}/modalidades/{general_id}/disponibilidad")
    assert resp_gen.status_code == 200
    assert resp_gen.json() == {"disponibles": 2}

    # Disponibilidad numerada inicial = cantidad de asientos libres (2)
    resp_num = await client.get(f"/eventos/{evento['id']}/modalidades/{numerada_id}/disponibilidad")
    assert resp_num.status_code == 200
    assert resp_num.json() == {"disponibles": 2}


async def test_obtener_disponibilidad_failsWhenModalidadNoExiste(client: AsyncClient):
    r = await client.post("/eventos", json=evento_payload())
    evento_id = r.json()["id"]

    resp = await client.get(f"/eventos/{evento_id}/modalidades/{uuid.uuid4()}/disponibilidad")
    assert resp.status_code == 404


async def test_reserva_general_ciclo_completo_y_disponibilidad(
    client: AsyncClient, evento_con_inventario_payload
):
    r = await client.post("/eventos", json=evento_con_inventario_payload)
    evento = r.json()
    general_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "general")

    # 1. Crear primera reserva general
    res1 = await client.post(f"/eventos/{evento['id']}/modalidades/{general_id}/reservas")
    assert res1.status_code == 201
    res1_id = res1.json()["reserva_id"]

    # Disponibilidad baja a 1
    disp1 = await client.get(f"/eventos/{evento['id']}/modalidades/{general_id}/disponibilidad")
    assert disp1.json() == {"disponibles": 1}

    # 2. Crear segunda reserva general (agota cupo)
    res2 = await client.post(f"/eventos/{evento['id']}/modalidades/{general_id}/reservas")
    assert res2.status_code == 201

    # Disponibilidad baja a 0
    disp2 = await client.get(f"/eventos/{evento['id']}/modalidades/{general_id}/disponibilidad")
    assert disp2.json() == {"disponibles": 0}

    # 3. Tercera reserva rechaza con 409 sin disponibilidad
    res3 = await client.post(f"/eventos/{evento['id']}/modalidades/{general_id}/reservas")
    assert res3.status_code == 409
    assert res3.json()["detail"] == "sin disponibilidad"

    # 4. Confirmar la primera reserva
    conf = await client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas/{res1_id}/confirmar"
    )
    assert conf.status_code == 200
    assert conf.json() == {"status": "confirmada"}

    # Reconfirmación es idempotente
    conf_re = await client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas/{res1_id}/confirmar"
    )
    assert conf_re.status_code == 200
    assert conf_re.json() == {"status": "confirmada"}

    # No se puede liberar una reserva ya confirmada
    lib_fail = await client.delete(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas/{res1_id}"
    )
    assert lib_fail.status_code == 409


async def test_reserva_numerada_ciclo_completo_y_liberacion(
    client: AsyncClient, evento_con_inventario_payload
):
    r = await client.post("/eventos", json=evento_con_inventario_payload)
    evento = r.json()
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento1 = numerada["sectores"][0]["asientos"][0]
    asiento2 = numerada["sectores"][0]["asientos"][1]

    # 1. Reservar asiento 1
    res1 = await client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento1["id"]},
    )
    assert res1.status_code == 201
    res1_id = res1.json()["reserva_id"]

    # 2. Intentar reservar el mismo asiento 1 rechaza con 409
    res1_dup = await client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento1["id"]},
    )
    assert res1_dup.status_code == 409
    assert res1_dup.json()["detail"] == "asiento no disponible"

    # 3. Liberar reserva del asiento 1
    lib1 = await client.delete(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas/{res1_id}"
    )
    assert lib1.status_code == 200
    assert lib1.json() == {"status": "liberada"}

    # No se puede volver a liberar
    lib1_re = await client.delete(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas/{res1_id}"
    )
    assert lib1_re.status_code == 409

    # No se puede confirmar una reserva liberada
    conf_lib = await client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas/{res1_id}/confirmar"
    )
    assert conf_lib.status_code == 409

    # 4. Ahora el asiento 1 vuelve a estar disponible para ser reservado
    res1_again = await client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento1["id"]},
    )
    assert res1_again.status_code == 201


async def test_idempotency_key_reintento_y_conflicto(
    client: AsyncClient, evento_con_inventario_payload
):
    r = await client.post("/eventos", json=evento_con_inventario_payload)
    evento = r.json()
    general_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "general")
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento1 = numerada["sectores"][0]["asientos"][0]
    asiento2 = numerada["sectores"][0]["asientos"][1]

    key = str(uuid.uuid4())

    # 1. Primera reserva con Idempotency-Key
    res = await client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas",
        headers={"Idempotency-Key": key},
    )
    assert res.status_code == 201
    reserva_id = res.json()["reserva_id"]

    # 2. Reintento con misma clave y mismo payload retorna la misma reserva
    reintento = await client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas",
        headers={"Idempotency-Key": key},
    )
    assert reintento.status_code == 200
    assert reintento.json()["reserva_id"] == reserva_id

    # 3. Reutilizar la misma clave para otra modalidad o con otro payload responde 409
    conflicto_mod = await client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        headers={"Idempotency-Key": key},
        json={"asiento_id": asiento1["id"]},
    )
    assert conflicto_mod.status_code == 409
    assert conflicto_mod.json()["detail"] == "idempotency_conflict"


async def test_idempotency_key_rescate_ultimo_cupo(
    client: AsyncClient, evento_con_inventario_payload
):
    r = await client.post("/eventos", json=evento_con_inventario_payload)
    evento = r.json()
    general_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "general")

    key_ultimo = "key-ultimo-cupo"

    # Reservar cupo 1
    await client.post(f"/eventos/{evento['id']}/modalidades/{general_id}/reservas")

    # Reservar cupo 2 con clave de idempotencia (agota cupo)
    r2 = await client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas",
        headers={"Idempotency-Key": key_ultimo},
    )
    assert r2.status_code == 201
    r2_id = r2.json()["reserva_id"]

    # Reintento cuando ya no hay cupo: rescata la reserva existente y devuelve 200 en vez de 409 sin disponibilidad
    r_retry = await client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas",
        headers={"Idempotency-Key": key_ultimo},
    )
    assert r_retry.status_code == 200
    assert r_retry.json()["reserva_id"] == r2_id


async def test_idempotency_key_rescate_mismo_asiento(
    client: AsyncClient, evento_con_inventario_payload
):
    r = await client.post("/eventos", json=evento_con_inventario_payload)
    evento = r.json()
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento = numerada["sectores"][0]["asientos"][0]

    key_asiento = "key-mismo-asiento"

    # Reservar asiento con clave
    r1 = await client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        headers={"Idempotency-Key": key_asiento},
        json={"asiento_id": asiento["id"]},
    )
    assert r1.status_code == 201
    r1_id = r1.json()["reserva_id"]

    # Reintento para el mismo asiento cuando ya está reservado: rescata la reserva y devuelve 200
    r_retry = await client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        headers={"Idempotency-Key": key_asiento},
        json={"asiento_id": asiento["id"]},
    )
    assert r_retry.status_code == 200
    assert r_retry.json()["reserva_id"] == r1_id

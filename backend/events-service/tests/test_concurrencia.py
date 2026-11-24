import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.models import Asiento, Reserva
from tests.conftest import evento_payload


@pytest.fixture
def evento_concurrencia_payload():
    return evento_payload(
        nombre="Evento Concurrencia",
        modalidades=[
            {
                "nombre": "General Test",
                "tipo": "general",
                "precio": "5000.00",
                "cupo": 2,
            },
            {
                "nombre": "Numerada Test",
                "tipo": "numerado",
                "sectores": [
                    {
                        "nombre": "Sector Concurrente",
                        "precio": "10000.00",
                        "asientos": [
                            {"fila": "1", "numero": 1},
                            {"fila": "1", "numero": 2},
                        ],
                    }
                ],
            },
        ],
    )


async def test_concurrencia_reserva_mismo_asiento(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    # 1. Crear evento
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    assert r.status_code == 201
    evento = r.json()
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento_id = numerada["sectores"][0]["asientos"][0]["id"]

    # 2. 5 solicitudes concurrentes compitiendo por el mismo asiento_id
    tasks = [
        concurrent_client.post(
            f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
            json={"asiento_id": asiento_id},
        )
        for _ in range(5)
    ]
    responses = await asyncio.gather(*tasks)

    # 3. Exactamente una debe ganar (201) y las otras 4 ser rechazadas (409)
    status_codes = [resp.status_code for resp in responses]
    assert status_codes.count(201) == 1
    assert status_codes.count(409) == 4

    conflicts = [r.json() for r in responses if r.status_code == 409]
    for c in conflicts:
        assert c["detail"] == "asiento no disponible"

    # 4. Asiento en base de datos debe figurar reservado
    async with session_factory() as session:
        asiento_db = await session.get(Asiento, uuid.UUID(asiento_id))
        assert asiento_db.estado == "reservado"


async def test_concurrencia_general_cupo_con_confirmadas(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    # 1. Crear evento con cupo 2
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    assert r.status_code == 201
    evento = r.json()
    general_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "general")

    # 2. Reservar y confirmar 1 cupo
    r1 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas"
    )
    assert r1.status_code == 201
    r1_id = r1.json()["reserva_id"]

    r_conf = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas/{r1_id}/confirmar"
    )
    assert r_conf.status_code == 200
    assert r_conf.json() == {"status": "confirmada"}

    # 3. Ahora queda 1 cupo disponible (cupo 2 - 1 confirmada).
    #    Lanzar 3 solicitudes concurrentes para el cupo remanente.
    tasks = [
        concurrent_client.post(
            f"/eventos/{evento['id']}/modalidades/{general_id}/reservas"
        )
        for _ in range(3)
    ]
    responses = await asyncio.gather(*tasks)

    # 4. Exactamente 1 solicitud debe ser admitida (201) y las otras 2 rechazadas (409)
    status_codes = [resp.status_code for resp in responses]
    assert status_codes.count(201) == 1
    assert status_codes.count(409) == 2

    for resp in responses:
        if resp.status_code == 409:
            assert resp.json()["detail"] == "sin disponibilidad"

    # 5. En DB debe haber exactamente 1 confirmada y 1 activa
    async with session_factory() as session:
        res = await session.scalars(
            select(Reserva).where(Reserva.modalidad_id == uuid.UUID(general_id))
        )
        reservas = res.all()
        assert len(reservas) == 2
        estados = [r.estado for r in reservas]
        assert estados.count("confirmada") == 1
        assert estados.count("activa") == 1


async def test_concurrencia_idempotencia_ultimo_cupo(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    # 1. Crear evento
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    evento = r.json()
    general_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "general")

    # 2. Tomar el primer cupo de 2
    r_first = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas"
    )
    assert r_first.status_code == 201

    # 3. Dos solicitudes concurrentes con la MISMA Idempotency-Key sobre el último cupo
    idem_key = f"key-ultimo-cupo-{uuid.uuid4()}"
    tasks = [
        concurrent_client.post(
            f"/eventos/{evento['id']}/modalidades/{general_id}/reservas",
            headers={"Idempotency-Key": idem_key},
            json={},
        )
        for _ in range(2)
    ]
    responses = await asyncio.gather(*tasks)

    # Ambas solicitudes deben retornar exitosas con el mismo reserva_id
    for resp in responses:
        assert resp.status_code in (200, 201)
    res_ids = [resp.json()["reserva_id"] for resp in responses]
    assert res_ids[0] == res_ids[1]

    # En DB no se debe haber superado el cupo total de 2
    async with session_factory() as session:
        res = await session.scalars(
            select(Reserva).where(Reserva.modalidad_id == uuid.UUID(general_id))
        )
        reservas = res.all()
        assert len(reservas) == 2


async def test_concurrencia_idempotencia_mismo_asiento(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    # 1. Crear evento
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    evento = r.json()
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento_id = numerada["sectores"][0]["asientos"][0]["id"]

    # 2. Dos solicitudes concurrentes con la MISMA Idempotency-Key
    #    sobre el mismo asiento
    idem_key = f"key-mismo-asiento-{uuid.uuid4()}"
    tasks = [
        concurrent_client.post(
            f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
            headers={"Idempotency-Key": idem_key},
            json={"asiento_id": asiento_id},
        )
        for _ in range(2)
    ]
    responses = await asyncio.gather(*tasks)

    # Ambas solicitudes deben retornar exitosas con el mismo reserva_id
    for resp in responses:
        assert resp.status_code in (200, 201)
    res_ids = [resp.json()["reserva_id"] for resp in responses]
    assert res_ids[0] == res_ids[1]

    # En DB debe haber exactamente 1 reserva persistida para ese asiento
    async with session_factory() as session:
        res = await session.scalars(
            select(Reserva).where(Reserva.asiento_id == uuid.UUID(asiento_id))
        )
        reservas = res.all()
        assert len(reservas) == 1


async def test_disponibilidad_tras_expiracion_reserva(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    evento = r.json()
    general_id = next(m["id"] for m in evento["modalidades"] if m["tipo"] == "general")
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento_id = numerada["sectores"][0]["asientos"][0]["id"]

    # 1. Agotar cupo general (2 reservas)
    r_g1 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas"
    )
    r_g2 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{general_id}/reservas"
    )
    assert r_g1.status_code == 201
    assert r_g2.status_code == 201

    # Disponibilidad general = 0
    disp_g0 = await concurrent_client.get(
        f"/eventos/{evento['id']}/modalidades/{general_id}/disponibilidad"
    )
    assert disp_g0.json() == {"disponibles": 0}

    # 2. Expirar la reserva r_g1 en la base de datos
    async with session_factory() as session:
        await session.execute(
            update(Reserva)
            .where(Reserva.id == uuid.UUID(r_g1.json()["reserva_id"]))
            .values(expira_en=datetime.now(timezone.utc) - timedelta(minutes=5))
        )
        await session.commit()

    # Disponibilidad general se recupera a 1 (r_g1 ya venció por TTL)
    disp_g1 = await concurrent_client.get(
        f"/eventos/{evento['id']}/modalidades/{general_id}/disponibilidad"
    )
    assert disp_g1.json() == {"disponibles": 1}

    # 3. Reservar asiento numerado
    r_num = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento_id},
    )
    assert r_num.status_code == 201

    # Disponibilidad numerada inicial = 2, tras 1 reserva pasa a 1
    disp_n1 = await concurrent_client.get(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/disponibilidad"
    )
    assert disp_n1.json() == {"disponibles": 1}

    # 4. Expirar la reserva numerada en base de datos
    async with session_factory() as session:
        await session.execute(
            update(Reserva)
            .where(Reserva.id == uuid.UUID(r_num.json()["reserva_id"]))
            .values(expira_en=datetime.now(timezone.utc) - timedelta(minutes=5))
        )
        await session.commit()

    # Disponibilidad numerada ejecuta lazy cleanup y recupera disponibilidad = 2
    disp_n2 = await concurrent_client.get(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/disponibilidad"
    )
    assert disp_n2.json() == {"disponibles": 2}

    # Verificar persistencia en BD tras el GET (Hallazgo 1: commit lazy cleanup)
    async with session_factory() as session:
        as_db = await session.get(Asiento, uuid.UUID(asiento_id))
        res_db = await session.get(Reserva, uuid.UUID(r_num.json()["reserva_id"]))
        assert as_db.estado == "libre"
        assert res_db.estado == "liberada"


async def test_confirmacion_idempotente_y_expirada(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    evento = r.json()
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento_id = numerada["sectores"][0]["asientos"][0]["id"]

    # 1. Crear reserva
    r_num = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento_id},
    )
    reserva_id = r_num.json()["reserva_id"]

    # 2. Confirmación exitosa -> 200 confirmada
    conf1 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas/{reserva_id}/confirmar"
    )
    assert conf1.status_code == 200
    assert conf1.json() == {"status": "confirmada"}

    # 3. Reconfirmación idempotente -> 200 confirmada
    conf2 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas/{reserva_id}/confirmar"
    )
    assert conf2.status_code == 200
    assert conf2.json() == {"status": "confirmada"}

    # 4. Crear otra reserva en asiento 2 y forzar su expiración
    asiento2_id = numerada["sectores"][0]["asientos"][1]["id"]
    r_num2 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento2_id},
    )
    reserva2_id = r_num2.json()["reserva_id"]

    async with session_factory() as session:
        await session.execute(
            update(Reserva)
            .where(Reserva.id == uuid.UUID(reserva2_id))
            .values(expira_en=datetime.now(timezone.utc) - timedelta(minutes=5))
        )
        await session.commit()

    # 5. Intentar confirmar reserva expirada -> 409 reserva expirada
    conf_exp = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas/{reserva2_id}/confirmar"
    )
    assert conf_exp.status_code == 409
    assert conf_exp.json()["detail"] == "reserva expirada"

    # Verificar que el asiento 2 se liberó y la reserva quedó en liberada
    async with session_factory() as session:
        as2 = await session.get(Asiento, uuid.UUID(asiento2_id))
        assert as2.estado == "libre"

        r2_db = await session.get(Reserva, uuid.UUID(reserva2_id))
        assert r2_db.estado == "liberada"


async def test_reserva_numerada_lazy_cleanup_al_reservar(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    evento = r.json()
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento_id = numerada["sectores"][0]["asientos"][0]["id"]

    # 1. Cliente 1 reserva el asiento
    r_c1 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento_id},
    )
    assert r_c1.status_code == 201
    r_c1_id = r_c1.json()["reserva_id"]

    # 2. Reserva del cliente 1 expira por TTL
    async with session_factory() as session:
        await session.execute(
            update(Reserva)
            .where(Reserva.id == uuid.UUID(r_c1_id))
            .values(expira_en=datetime.now(timezone.utc) - timedelta(minutes=15))
        )
        await session.commit()

    # 3. Cliente 2 solicita reservar ese mismo asiento
    #    El endpoint debe ejecutar lazy cleanup, liberar r_c1 y asignar el asiento a c2
    r_c2 = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento_id},
    )
    assert r_c2.status_code == 201
    r_c2_id = r_c2.json()["reserva_id"]
    assert r_c2_id != r_c1_id

    # 4. En DB: r_c1 está liberada, r_c2 está activa, asiento está reservado
    async with session_factory() as session:
        r1_db = await session.get(Reserva, uuid.UUID(r_c1_id))
        assert r1_db.estado == "liberada"

        r2_db = await session.get(Reserva, uuid.UUID(r_c2_id))
        assert r2_db.estado == "activa"

        asiento_db = await session.get(Asiento, uuid.UUID(asiento_id))
        assert asiento_db.estado == "reservado"


async def test_confirmacion_defensiva_asiento_no_reservado(
    concurrent_client: AsyncClient,
    session_factory,
    evento_concurrencia_payload,
):
    r = await concurrent_client.post("/eventos", json=evento_concurrencia_payload)
    evento = r.json()
    numerada = next(m for m in evento["modalidades"] if m["tipo"] == "numerado")
    asiento_id = numerada["sectores"][0]["asientos"][0]["id"]

    r_num = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas",
        json={"asiento_id": asiento_id},
    )
    res_id = uuid.UUID(r_num.json()["reserva_id"])

    # Modificar directamente el asiento en BD a libre simulando inconsistencia externa
    async with session_factory() as session:
        await session.execute(
            update(Asiento)
            .where(Asiento.id == uuid.UUID(asiento_id))
            .values(estado="libre")
        )
        await session.commit()

    # Confirmar reserva
    conf = await concurrent_client.post(
        f"/eventos/{evento['id']}/modalidades/{numerada['id']}/reservas/{res_id}/confirmar"
    )
    assert conf.status_code == 200

    # Comprobar que la validación defensiva impidió cambiar el asiento a vendido
    async with session_factory() as session:
        as_db = await session.get(Asiento, uuid.UUID(asiento_id))
        assert as_db.estado == "libre"


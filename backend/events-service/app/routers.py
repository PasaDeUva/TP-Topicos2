import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.identity import current_organizer
from app.models import Asiento, Evento, Modalidad, Reserva, Sector
from app.schemas import (
    ConfirmacionOut,
    DisponibilidadOut,
    EventoIn,
    EventoOut,
    LiberacionOut,
    ReservaIn,
    ReservaOut,
)

router = APIRouter(prefix="/eventos", tags=["eventos"])


def _load_options():
    return (
        selectinload(Evento.modalidades)
        .selectinload(Modalidad.sectores)
        .selectinload(Sector.asientos)
    )


def _crear_modalidad(m) -> Modalidad:
    if m.tipo == "general":
        return Modalidad(
            nombre=m.nombre,
            tipo=m.tipo,
            precio=m.precio,
            cupo=m.cupo,
        )
    mod = Modalidad(
        nombre=m.nombre,
        tipo=m.tipo,
        precio=None,
        cupo=None,
    )
    for s in m.sectores:
        sec = Sector(
            nombre=s.nombre,
            precio=s.precio,
            modalidad=mod,
        )
        for a in s.asientos:
            Asiento(
                fila=a.fila,
                numero=a.numero,
                estado="libre",
                sector=sec,
            )
    return mod


@router.get("", response_model=list[EventoOut])
async def listar_eventos(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Evento)
        .options(_load_options())
        .order_by(Evento.creado_en.asc())
    )
    return result.scalars().all()


@router.get("/{evento_id}", response_model=EventoOut)
async def obtener_evento(
    evento_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Evento)
        .where(Evento.id == evento_id)
        .options(_load_options())
    )
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=404, detail="not found")
    return evento


@router.post("", response_model=EventoOut, status_code=201)
async def crear_evento(
    payload: EventoIn,
    owner: uuid.UUID = Depends(current_organizer),
    session: AsyncSession = Depends(get_session),
):
    if payload.owner_id is not None and payload.owner_id != owner:
        raise HTTPException(status_code=403, detail="forbidden")
    evento = Evento(
        owner_id=owner,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        venue=payload.venue,
        fecha=payload.fecha,
    )
    evento.modalidades = [_crear_modalidad(m) for m in payload.modalidades]
    session.add(evento)
    await session.commit()
    await session.refresh(evento, ["modalidades"])
    # Recargar con relaciones anidadas
    return await obtener_evento(evento.id, session)


@router.put("/{evento_id}", response_model=EventoOut)
async def editar_evento(
    evento_id: uuid.UUID,
    payload: EventoIn,
    owner: uuid.UUID = Depends(current_organizer),
    session: AsyncSession = Depends(get_session),
):
    if payload.owner_id is not None and payload.owner_id != owner:
        raise HTTPException(status_code=403, detail="forbidden")
    result = await session.execute(
        select(Evento)
        .where(Evento.id == evento_id)
        .options(_load_options())
    )
    evento = result.scalar_one_or_none()
    if evento is None or evento.owner_id != owner:
        raise HTTPException(status_code=404, detail="not found")

    # Mapeo de modalidades existentes por ID
    existentes = {m.id: m for m in evento.modalidades}
    nuevas_ids = {m.id for m in payload.modalidades if m.id is not None}

    # Guard de auditoría / integridad: comprobar reservas en modalidades a eliminar
    a_eliminar = [m for m_id, m in existentes.items() if m_id not in nuevas_ids]
    for m_del in a_eliminar:
        count_reservas = await session.scalar(
            select(func.count(Reserva.id)).where(Reserva.modalidad_id == m_del.id)
        )
        if count_reservas and count_reservas > 0:
            raise HTTPException(
                status_code=409,
                detail="no se puede eliminar modalidad con historial de reservas",
            )

    # Validar que no se intente cambiar el tipo de una modalidad existente (Hallazgo 2)
    for m_in in payload.modalidades:
        if m_in.id is not None and m_in.id in existentes:
            if m_in.tipo != existentes[m_in.id].tipo:
                raise HTTPException(
                    status_code=400,
                    detail="no se permite cambiar el tipo de una modalidad existente",
                )

    evento.nombre = payload.nombre
    evento.descripcion = payload.descripcion
    evento.venue = payload.venue
    evento.fecha = payload.fecha

    # Actualizar modalidades preservadas o agregar nuevas
    modalidades_actualizadas = []
    for m_in in payload.modalidades:
        if m_in.id is not None and m_in.id in existentes:
            mod = existentes[m_in.id]
            mod.nombre = m_in.nombre
            if m_in.tipo == "general":
                mod.precio = m_in.precio
                mod.cupo = m_in.cupo
            modalidades_actualizadas.append(mod)
        else:
            modalidades_actualizadas.append(_crear_modalidad(m_in))

    evento.modalidades = modalidades_actualizadas
    await session.commit()
    return await obtener_evento(evento.id, session)


@router.delete("/{evento_id}", response_model=EventoOut)
async def eliminar_evento(
    evento_id: uuid.UUID,
    owner: uuid.UUID = Depends(current_organizer),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Evento)
        .where(Evento.id == evento_id)
        .options(_load_options())
    )
    evento = result.scalar_one_or_none()
    if evento is None or evento.owner_id != owner:
        raise HTTPException(status_code=404, detail="not found")

    evento.activo = False
    await session.commit()
    return evento


# ---------------------------------------------------------------------------
# Endpoints de Inventario y Reservas
# ---------------------------------------------------------------------------


async def _get_modalidad_o_404(
    evento_id: uuid.UUID, modalidad_id: uuid.UUID, session: AsyncSession
) -> tuple[Evento, Modalidad]:
    result = await session.execute(
        select(Evento)
        .where(Evento.id == evento_id)
        .options(_load_options())
    )
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=404, detail="evento not found")
    modalidad = next((m for m in evento.modalidades if m.id == modalidad_id), None)
    if modalidad is None:
        raise HTTPException(status_code=404, detail="modalidad not found")
    return evento, modalidad


async def _lazy_cleanup_reservas_vencidas(
    modalidad_id: uuid.UUID, session: AsyncSession
) -> bool:
    # 1. Liberación perezosa de reservas activas vencidas (Lock en reservas primero)
    now = datetime.now(timezone.utc)
    vencidas = await session.scalars(
        select(Reserva)
        .where(
            Reserva.modalidad_id == modalidad_id,
            Reserva.estado == "activa",
            Reserva.expira_en <= now,
        )
        .with_for_update()
    )
    liberadas = False
    for r in vencidas:
        r.estado = "liberada"
        liberadas = True
        if r.asiento_id:
            # 2. Lock en asiento y verificación defensiva de pertenencia activa
            asiento = await session.scalar(
                select(Asiento)
                .where(Asiento.id == r.asiento_id)
                .with_for_update()
            )
            if asiento and asiento.estado == "reservado":
                asiento.estado = "libre"
    await session.flush()
    return liberadas


@router.get(
    "/{evento_id}/modalidades/{modalidad_id}/disponibilidad",
    response_model=DisponibilidadOut,
)
async def obtener_disponibilidad(
    evento_id: uuid.UUID,
    modalidad_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    evento, modalidad = await _get_modalidad_o_404(evento_id, modalidad_id, session)
    now = datetime.now(timezone.utc)

    if modalidad.tipo == "general":
        ocupadas = await session.scalar(
            select(func.count(Reserva.id)).where(
                Reserva.modalidad_id == modalidad.id,
                Reserva.estado.in_(["activa", "confirmada"]),
                or_(Reserva.estado == "confirmada", Reserva.expira_en > now),
            )
        )
        disponibles = max(0, (modalidad.cupo or 0) - (ocupadas or 0))
        return {"disponibles": disponibles}

    # Para modalidad numerada: lazy cleanup previo para restaurar asientos vencidos
    hubo_liberacion = await _lazy_cleanup_reservas_vencidas(modalidad.id, session)
    if hubo_liberacion:
        await session.commit()

    disponibles = await session.scalar(
        select(func.count(Asiento.id))
        .join(Sector)
        .where(Sector.modalidad_id == modalidad.id, Asiento.estado == "libre")
    )
    return {"disponibles": disponibles or 0}


@router.post(
    "/{evento_id}/modalidades/{modalidad_id}/reservas",
    response_model=ReservaOut,
    status_code=201,
)
async def crear_reserva(
    evento_id: uuid.UUID,
    modalidad_id: uuid.UUID,
    payload: ReservaIn = ReservaIn(),
    response: Response = None,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=255),
    session: AsyncSession = Depends(get_session),
):
    evento, modalidad = await _get_modalidad_o_404(evento_id, modalidad_id, session)
    if not evento.activo:
        raise HTTPException(status_code=409, detail="evento inactivo")

    # 1. Consulta inicial por Idempotency-Key si ya fue procesada
    if idempotency_key:
        reserva_existente = await session.scalar(
            select(Reserva).where(Reserva.idempotency_key == idempotency_key)
        )
        if reserva_existente:
            if (
                reserva_existente.modalidad_id == modalidad_id
                and reserva_existente.asiento_id == payload.asiento_id
            ):
                if response:
                    response.status_code = 200
                return {"reserva_id": reserva_existente.id}
            raise HTTPException(status_code=409, detail="idempotency_conflict")

    now = datetime.now(timezone.utc)
    expira = now + timedelta(minutes=settings.reserva_ttl_minutes)

    if modalidad.tipo == "general":
        modalidad_lock = await session.scalar(
            select(Modalidad)
            .where(Modalidad.id == modalidad.id)
            .with_for_update()
        )
        cupo_total = modalidad_lock.cupo if modalidad_lock else (modalidad.cupo or 0)

        ocupadas = await session.scalar(
            select(func.count(Reserva.id)).where(
                Reserva.modalidad_id == modalidad.id,
                Reserva.estado.in_(["activa", "confirmada"]),
                or_(Reserva.estado == "confirmada", Reserva.expira_en > now),
            )
        )
        if (ocupadas or 0) >= (cupo_total or 0):
            # Rescate previo al 409 si concurrió con la misma clave
            if idempotency_key:
                reserva_existente = await session.scalar(
                    select(Reserva).where(Reserva.idempotency_key == idempotency_key)
                )
                if reserva_existente:
                    if (
                        reserva_existente.modalidad_id == modalidad_id
                        and reserva_existente.asiento_id is None
                    ):
                        if response:
                            response.status_code = 200
                        return {"reserva_id": reserva_existente.id}
                    raise HTTPException(status_code=409, detail="idempotency_conflict")
            raise HTTPException(status_code=409, detail="sin disponibilidad")

        nueva_reserva = Reserva(
            modalidad_id=modalidad.id,
            asiento_id=None,
            estado="activa",
            expira_en=expira,
            idempotency_key=idempotency_key,
        )
        try:
            async with session.begin_nested():
                session.add(nueva_reserva)
                await session.flush()
        except IntegrityError:
            if idempotency_key:
                reserva_existente = await session.scalar(
                    select(Reserva).where(Reserva.idempotency_key == idempotency_key)
                )
                if (
                    reserva_existente
                    and reserva_existente.modalidad_id == modalidad_id
                    and reserva_existente.asiento_id is None
                ):
                    if response:
                        response.status_code = 200
                    return {"reserva_id": reserva_existente.id}
                raise HTTPException(status_code=409, detail="idempotency_conflict")
            raise

        await session.commit()
        return {"reserva_id": nueva_reserva.id}

    # Modalidad Numerada
    if not payload.asiento_id:
        raise HTTPException(
            status_code=400, detail="asiento_id requerido para modalidad numerada"
        )

    # Validar que el asiento pertenezca a la modalidad
    asiento = await session.scalar(
        select(Asiento)
        .join(Sector)
        .where(
            Sector.modalidad_id == modalidad.id,
            Asiento.id == payload.asiento_id,
        )
    )
    if not asiento:
        raise HTTPException(status_code=404, detail="asiento not found")

    # Lazy cleanup sobre reservas vencidas para esta modalidad
    await _lazy_cleanup_reservas_vencidas(modalidad.id, session)

    stmt = (
        update(Asiento)
        .where(Asiento.id == payload.asiento_id, Asiento.estado == "libre")
        .values(estado="reservado")
    )
    res_upd = await session.execute(stmt)
    if res_upd.rowcount == 0:
        # Rescate previo al 409 si concurrió con la misma clave
        if idempotency_key:
            reserva_existente = await session.scalar(
                select(Reserva).where(Reserva.idempotency_key == idempotency_key)
            )
            if reserva_existente:
                if (
                    reserva_existente.modalidad_id == modalidad_id
                    and reserva_existente.asiento_id == payload.asiento_id
                ):
                    if response:
                        response.status_code = 200
                    return {"reserva_id": reserva_existente.id}
                raise HTTPException(status_code=409, detail="idempotency_conflict")
        raise HTTPException(status_code=409, detail="asiento no disponible")

    nueva_reserva = Reserva(
        modalidad_id=modalidad.id,
        asiento_id=payload.asiento_id,
        estado="activa",
        expira_en=expira,
        idempotency_key=idempotency_key,
    )
    try:
        async with session.begin_nested():
            session.add(nueva_reserva)
            await session.flush()
    except IntegrityError:
        if idempotency_key:
            reserva_existente = await session.scalar(
                select(Reserva).where(Reserva.idempotency_key == idempotency_key)
            )
            if (
                reserva_existente
                and reserva_existente.modalidad_id == modalidad_id
                and reserva_existente.asiento_id == payload.asiento_id
            ):
                if response:
                    response.status_code = 200
                return {"reserva_id": reserva_existente.id}
            raise HTTPException(status_code=409, detail="idempotency_conflict")
        raise

    await session.commit()
    return {"reserva_id": nueva_reserva.id}


@router.delete(
    "/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}",
    response_model=LiberacionOut,
)
async def liberar_reserva(
    evento_id: uuid.UUID,
    modalidad_id: uuid.UUID,
    reserva_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    await _get_modalidad_o_404(evento_id, modalidad_id, session)

    reserva = await session.scalar(
        select(Reserva)
        .where(
            Reserva.id == reserva_id,
            Reserva.modalidad_id == modalidad_id,
        )
        .with_for_update()
    )
    if not reserva:
        raise HTTPException(status_code=404, detail="reserva not found")

    if reserva.estado in ("liberada", "confirmada"):
        raise HTTPException(
            status_code=409, detail=f"reserva ya se encuentra {reserva.estado}"
        )

    reserva.estado = "liberada"
    if reserva.asiento_id:
        asiento = await session.scalar(
            select(Asiento)
            .where(Asiento.id == reserva.asiento_id)
            .with_for_update()
        )
        if asiento and asiento.estado == "reservado":
            asiento.estado = "libre"

    await session.commit()
    return {"status": "liberada"}


@router.post(
    "/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}/confirmar",
    response_model=ConfirmacionOut,
)
async def confirmar_reserva(
    evento_id: uuid.UUID,
    modalidad_id: uuid.UUID,
    reserva_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    await _get_modalidad_o_404(evento_id, modalidad_id, session)

    reserva = await session.scalar(
        select(Reserva)
        .where(
            Reserva.id == reserva_id,
            Reserva.modalidad_id == modalidad_id,
        )
        .with_for_update()
    )
    if not reserva:
        raise HTTPException(status_code=404, detail="reserva not found")

    if reserva.estado == "confirmada":
        return {"status": "confirmada"}

    if reserva.estado == "liberada":
        raise HTTPException(status_code=409, detail="reserva liberada")

    now = datetime.now(timezone.utc)
    if reserva.expira_en <= now:
        reserva.estado = "liberada"
        if reserva.asiento_id:
            asiento = await session.scalar(
                select(Asiento)
                .where(Asiento.id == reserva.asiento_id)
                .with_for_update()
            )
            if asiento and asiento.estado == "reservado":
                asiento.estado = "libre"
        await session.commit()
        raise HTTPException(status_code=409, detail="reserva expirada")

    reserva.estado = "confirmada"
    if reserva.asiento_id:
        asiento = await session.scalar(
            select(Asiento)
            .where(Asiento.id == reserva.asiento_id)
            .with_for_update()
        )
        if asiento and asiento.estado == "reservado":
            asiento.estado = "vendido"

    await session.commit()
    return {"status": "confirmada"}

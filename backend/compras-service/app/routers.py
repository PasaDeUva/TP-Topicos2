import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.events_client import EventsClient, EventsServiceError, get_events_client
from app.models import Compra
from app.schemas import CompraIn, CompraOut

router = APIRouter(prefix="/compras", tags=["compras"])


async def _buscar_por_clave(
    session: AsyncSession, cliente_id: uuid.UUID, idempotency_key: str
) -> Compra | None:
    result = await session.execute(
        select(Compra).where(
            Compra.cliente_id == cliente_id,
            Compra.idempotency_key == idempotency_key,
        )
    )
    return result.scalar_one_or_none()


def _responder_existente(
    existente: Compra, payload: CompraIn, response: Response
) -> Compra:
    if (
        existente.evento_id != payload.evento_id
        or existente.modalidad_id != payload.modalidad_id
    ):
        raise HTTPException(status_code=409, detail="idempotency conflict")
    response.status_code = 200
    return existente


@router.get("", response_model=list[CompraOut])
async def listar_compras(
    cliente_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Compra)
        .where(Compra.cliente_id == cliente_id)
        .order_by(Compra.creado_en.desc())
    )
    return result.scalars().all()


@router.get("/{compra_id}", response_model=CompraOut)
async def obtener_compra(
    compra_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    compra = await session.get(Compra, compra_id)
    if compra is None:
        raise HTTPException(status_code=404, detail="not found")
    return compra


@router.post("", response_model=CompraOut, status_code=201)
async def crear_compra(
    payload: CompraIn,
    response: Response,
    request: Request,
    idempotency_key: str = Header(..., min_length=1, max_length=255),
    session: AsyncSession = Depends(get_session),
    events_client: EventsClient = Depends(get_events_client),
):
    existente = await _buscar_por_clave(session, payload.cliente_id, idempotency_key)
    if existente is not None:
        return _responder_existente(existente, payload, response)

    try:
        evento = await events_client.obtener_evento(
            payload.evento_id, request.state.correlation_id
        )
    except EventsServiceError:
        raise HTTPException(status_code=503, detail="events service unavailable")

    if evento is None:
        raise HTTPException(status_code=404, detail="not found")

    modalidad = next(
        (m for m in evento["modalidades"] if m["id"] == str(payload.modalidad_id)),
        None,
    )
    if modalidad is None:
        raise HTTPException(status_code=404, detail="not found")
    if not evento["activo"]:
        raise HTTPException(status_code=409, detail="evento inactivo")
    if modalidad["tipo"] != "general":
        raise HTTPException(status_code=409, detail="modalidad no disponible")

    compra = Compra(
        cliente_id=payload.cliente_id,
        evento_id=payload.evento_id,
        modalidad_id=payload.modalidad_id,
        idempotency_key=idempotency_key,
    )
    session.add(compra)
    try:
        await session.commit()
    except IntegrityError:
        # Otra solicitud con la misma clave ganó la carrera: releer y comparar.
        await session.rollback()
        existente = await _buscar_por_clave(
            session, payload.cliente_id, idempotency_key
        )
        if existente is None:
            raise
        return _responder_existente(existente, payload, response)

    await session.refresh(compra)
    return compra

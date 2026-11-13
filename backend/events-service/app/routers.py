import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Evento, Modalidad
from app.schemas import EventoIn, EventoOut

router = APIRouter(prefix="/eventos", tags=["eventos"])


def _build_modalidades(evento: Evento, payload: EventoIn) -> None:
    """Reemplaza las modalidades del evento con las del payload."""
    evento.modalidades = [
        Modalidad(nombre=m.nombre, tipo=m.tipo) for m in payload.modalidades
    ]


@router.get("", response_model=list[EventoOut])
async def listar_eventos(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Evento).options(selectinload(Evento.modalidades))
    )
    return result.scalars().all()


@router.get("/{evento_id}", response_model=EventoOut)
async def obtener_evento(
    evento_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Evento)
        .where(Evento.id == evento_id)
        .options(selectinload(Evento.modalidades))
    )
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=404, detail="not found")
    return evento


@router.post("", response_model=EventoOut, status_code=201)
async def crear_evento(
    payload: EventoIn, session: AsyncSession = Depends(get_session)
):
    evento = Evento(
        owner_id=payload.owner_id,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        venue=payload.venue,
        fecha=payload.fecha,
    )
    _build_modalidades(evento, payload)
    session.add(evento)
    await session.commit()
    await session.refresh(evento, ["modalidades"])
    return evento


@router.put("/{evento_id}", response_model=EventoOut)
async def editar_evento(
    evento_id: uuid.UUID,
    payload: EventoIn,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Evento)
        .where(Evento.id == evento_id)
        .options(selectinload(Evento.modalidades))
    )
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=404, detail="not found")

    evento.owner_id = payload.owner_id
    evento.nombre = payload.nombre
    evento.descripcion = payload.descripcion
    evento.venue = payload.venue
    evento.fecha = payload.fecha
    _build_modalidades(evento, payload)

    await session.commit()
    await session.refresh(evento, ["modalidades"])
    return evento


@router.delete("/{evento_id}", response_model=EventoOut)
async def eliminar_evento(
    evento_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Evento)
        .where(Evento.id == evento_id)
        .options(selectinload(Evento.modalidades))
    )
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=404, detail="not found")

    evento.activo = False
    await session.commit()
    await session.refresh(evento, ["modalidades"])
    return evento

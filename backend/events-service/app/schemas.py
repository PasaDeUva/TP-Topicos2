import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ModalidadIn(BaseModel):
    nombre: str
    tipo: Literal["numerado", "general"]


class ModalidadOut(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo: str

    model_config = {"from_attributes": True}


class EventoIn(BaseModel):
    owner_id: uuid.UUID
    nombre: str
    descripcion: str | None = None
    venue: str
    fecha: datetime
    modalidades: list[ModalidadIn]


class EventoOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    nombre: str
    descripcion: str | None
    venue: str
    fecha: datetime
    activo: bool
    creado_en: datetime
    modalidades: list[ModalidadOut]

    model_config = {"from_attributes": True}

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ModalidadIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    tipo: Literal["numerado", "general"]


class ModalidadOut(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo: str

    model_config = {"from_attributes": True}


class EventoIn(BaseModel):
    owner_id: uuid.UUID | None = None
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = None
    venue: str = Field(min_length=1, max_length=255)
    fecha: datetime
    modalidades: list[ModalidadIn] = Field(min_length=1)

    @field_validator("fecha")
    @classmethod
    def validate_fecha_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("fecha must include timezone offset")
        return v


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

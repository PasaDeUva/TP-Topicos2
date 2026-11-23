import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AsientoIn(BaseModel):
    fila: str = Field(min_length=1, max_length=10)
    numero: int = Field(ge=1)


class AsientoOut(BaseModel):
    id: uuid.UUID
    fila: str
    numero: int
    estado: str

    model_config = {"from_attributes": True}


class SectorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    precio: Decimal = Field(ge=0)
    asientos: list[AsientoIn] = Field(min_length=1)


class SectorOut(BaseModel):
    id: uuid.UUID
    nombre: str
    precio: Decimal
    asientos: list[AsientoOut] = []

    model_config = {"from_attributes": True}


class ModalidadIn(BaseModel):
    id: uuid.UUID | None = None
    nombre: str = Field(min_length=1, max_length=100)
    tipo: Literal["numerado", "general"]
    precio: Decimal | None = None
    cupo: int | None = None
    sectores: list[SectorIn] = []

    @model_validator(mode="after")
    def validate_tipo_fields(self) -> "ModalidadIn":
        if self.tipo == "general":
            if self.precio is None or self.precio < 0:
                raise ValueError("precio es obligatorio y >= 0 en modalidad general")
            if self.cupo is None or self.cupo < 0:
                raise ValueError("cupo es obligatorio y >= 0 en modalidad general")
            if self.sectores:
                raise ValueError("modalidad general no admite sectores")
        elif self.tipo == "numerado":
            if self.precio is not None or self.cupo is not None:
                raise ValueError("modalidad numerada no admite precio ni cupo directo")
            if not self.sectores:
                raise ValueError("modalidad numerada requiere al menos un sector")
        return self


class ModalidadOut(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo: str
    precio: Decimal | None = None
    cupo: int | None = None
    sectores: list[SectorOut] = []

    model_config = {"from_attributes": True}


class EventoIn(BaseModel):
    owner_id: uuid.UUID
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


class DisponibilidadOut(BaseModel):
    disponibles: int


class ReservaIn(BaseModel):
    asiento_id: uuid.UUID | None = None


class ReservaOut(BaseModel):
    reserva_id: uuid.UUID


class ConfirmacionOut(BaseModel):
    status: str


class LiberacionOut(BaseModel):
    status: str

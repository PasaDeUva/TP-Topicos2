import uuid
from datetime import datetime

from pydantic import BaseModel


class CompraIn(BaseModel):
    cliente_id: uuid.UUID | None = None
    evento_id: uuid.UUID
    modalidad_id: uuid.UUID
    asiento_id: uuid.UUID | None = None


class CompraOut(BaseModel):
    id: uuid.UUID
    cliente_id: uuid.UUID
    evento_id: uuid.UUID
    modalidad_id: uuid.UUID
    reserva_id: uuid.UUID
    asiento_id: uuid.UUID | None = None
    estado: str
    creado_en: datetime

    model_config = {"from_attributes": True}

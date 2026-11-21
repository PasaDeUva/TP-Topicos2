import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Compra(Base):
    __tablename__ = "compras"
    __table_args__ = (
        UniqueConstraint(
            "cliente_id", "idempotency_key", name="uq_compras_cliente_idempotency"
        ),
        Index("ix_compras_cliente_creado", "cliente_id", text("creado_en DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    evento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    modalidad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

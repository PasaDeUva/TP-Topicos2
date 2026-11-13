import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[datetime] = mapped_column(nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    modalidades: Mapped[list["Modalidad"]] = relationship(
        "Modalidad", back_populates="evento", cascade="all, delete-orphan"
    )


class Modalidad(Base):
    __tablename__ = "modalidades"
    __table_args__ = (CheckConstraint("tipo IN ('numerado', 'general')", name="ck_modalidades_tipo"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eventos.id", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)

    evento: Mapped["Evento"] = relationship("Evento", back_populates="modalidades")

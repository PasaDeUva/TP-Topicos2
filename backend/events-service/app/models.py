from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    modalidades: Mapped[list["Modalidad"]] = relationship(
        "Modalidad", back_populates="evento", cascade="all, delete-orphan"
    )


class Modalidad(Base):
    __tablename__ = "modalidades"
    __table_args__ = (
        CheckConstraint("tipo IN ('numerado', 'general')", name="ck_modalidades_tipo"),
        CheckConstraint(
            "(tipo = 'general' AND precio IS NOT NULL AND precio >= 0 AND cupo IS NOT NULL AND cupo >= 0) "
            "OR (tipo = 'numerado' AND precio IS NULL AND cupo IS NULL)",
            name="ck_modalidades_precio_cupo",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    precio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    cupo: Mapped[int | None] = mapped_column(Integer, nullable=True)

    evento: Mapped["Evento"] = relationship("Evento", back_populates="modalidades")
    sectores: Mapped[list["Sector"]] = relationship(
        "Sector", back_populates="modalidad", cascade="all, delete-orphan"
    )
    reservas: Mapped[list["Reserva"]] = relationship(
        "Reserva", back_populates="modalidad"
    )


class Sector(Base):
    __tablename__ = "sectores"
    __table_args__ = (
        CheckConstraint("precio >= 0", name="ck_sectores_precio"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    modalidad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modalidades.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    modalidad: Mapped["Modalidad"] = relationship("Modalidad", back_populates="sectores")
    asientos: Mapped[list["Asiento"]] = relationship(
        "Asiento", back_populates="sector", cascade="all, delete-orphan"
    )


class Asiento(Base):
    __tablename__ = "asientos"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('libre', 'reservado', 'vendido')", name="ck_asientos_estado"
        ),
        UniqueConstraint(
            "sector_id", "fila", "numero", name="uq_asientos_sector_fila_numero"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sectores.id", ondelete="CASCADE"),
        nullable=False,
    )
    fila: Mapped[str] = mapped_column(String(10), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="libre")

    sector: Mapped["Sector"] = relationship("Sector", back_populates="asientos")
    reservas: Mapped[list["Reserva"]] = relationship("Reserva", back_populates="asiento")


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('activa', 'confirmada', 'liberada')", name="ck_reservas_estado"
        ),
        UniqueConstraint("idempotency_key", name="uq_reservas_idempotency_key"),
        Index("ix_reservas_modalidad_estado", "modalidad_id", "estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    modalidad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modalidades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asiento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asientos.id", ondelete="RESTRICT"),
        nullable=True,
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    modalidad: Mapped["Modalidad"] = relationship("Modalidad", back_populates="reservas")
    asiento: Mapped["Asiento | None"] = relationship("Asiento", back_populates="reservas")

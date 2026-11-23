"""add inventario, sectores, asientos y reservas

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-23
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Columnas precio y cupo en modalidades
    op.add_column("modalidades", sa.Column("precio", sa.Numeric(10, 2), nullable=True))
    op.add_column("modalidades", sa.Column("cupo", sa.Integer(), nullable=True))

    # 2. Backfill para registros preexistentes (exclusivo para general)
    op.execute(
        "UPDATE modalidades SET precio = 0.00 "
        "WHERE tipo = 'general' AND precio IS NULL;"
    )
    op.execute(
        "UPDATE modalidades SET cupo = 0 WHERE tipo = 'general' AND cupo IS NULL;"
    )

    # 3. Restricción de consistencia según el tipo de modalidad
    op.create_check_constraint(
        "ck_modalidades_precio_cupo",
        "modalidades",
        "(tipo = 'general' AND precio IS NOT NULL AND precio >= 0 "
        "AND cupo IS NOT NULL AND cupo >= 0) "
        "OR (tipo = 'numerado' AND precio IS NULL AND cupo IS NULL)",
    )

    # 4. Tabla sectores
    op.create_table(
        "sectores",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "modalidad_id",
            UUID(as_uuid=True),
            sa.ForeignKey("modalidades.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("precio", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("precio >= 0", name="ck_sectores_precio"),
    )

    # 5. Tabla asientos
    op.create_table(
        "asientos",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "sector_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sectores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fila", sa.String(10), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'libre'"),
        ),
        sa.CheckConstraint(
            "estado IN ('libre', 'reservado', 'vendido')", name="ck_asientos_estado"
        ),
        sa.UniqueConstraint(
            "sector_id", "fila", "numero", name="uq_asientos_sector_fila_numero"
        ),
    )

    # 6. Tabla reservas
    op.create_table(
        "reservas",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "modalidad_id",
            UUID(as_uuid=True),
            sa.ForeignKey("modalidades.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "asiento_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asientos.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'activa'"),
        ),
        sa.Column("expira_en", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.CheckConstraint(
            "estado IN ('activa', 'confirmada', 'liberada')", name="ck_reservas_estado"
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_reservas_idempotency_key"
        ),
    )
    op.create_index(
        "ix_reservas_modalidad_estado", "reservas", ["modalidad_id", "estado"]
    )


def downgrade() -> None:
    op.drop_index("ix_reservas_modalidad_estado", table_name="reservas")
    op.drop_table("reservas")
    op.drop_table("asientos")
    op.drop_table("sectores")
    op.drop_constraint("ck_modalidades_precio_cupo", "modalidades", type_="check")
    op.drop_column("modalidades", "cupo")
    op.drop_column("modalidades", "precio")

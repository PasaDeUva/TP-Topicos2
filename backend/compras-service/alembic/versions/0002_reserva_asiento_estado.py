"""reserva asiento estado

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
    op.add_column(
        "compras",
        sa.Column(
            "reserva_id",
            UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    # Remove server_default para que no se use por defecto en inserts de aplicación
    op.alter_column("compras", "reserva_id", server_default=None)
    op.add_column(
        "compras",
        sa.Column("asiento_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "compras",
        sa.Column(
            "estado",
            sa.String(length=32),
            nullable=False,
            server_default="confirmada",
        ),
    )
    op.create_index("ix_compras_reserva_id", "compras", ["reserva_id"])


def downgrade() -> None:
    op.drop_index("ix_compras_reserva_id", table_name="compras")
    op.drop_column("compras", "estado")
    op.drop_column("compras", "asiento_id")
    op.drop_column("compras", "reserva_id")

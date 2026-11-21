"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compras",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("cliente_id", UUID(as_uuid=True), nullable=False),
        sa.Column("evento_id", UUID(as_uuid=True), nullable=False),
        sa.Column("modalidad_id", UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "cliente_id", "idempotency_key", name="uq_compras_cliente_idempotency"
        ),
    )
    op.create_index(
        "ix_compras_cliente_creado",
        "compras",
        ["cliente_id", sa.text("creado_en DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_compras_cliente_creado", table_name="compras")
    op.drop_table("compras")

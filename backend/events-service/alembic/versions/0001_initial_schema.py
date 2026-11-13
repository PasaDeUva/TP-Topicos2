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
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "eventos",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("venue", sa.String(255), nullable=False),
        sa.Column("fecha", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "modalidades",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "evento_id",
            UUID(as_uuid=True),
            sa.ForeignKey("eventos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('numerado', 'general')", name="ck_modalidades_tipo"
        ),
    )


def downgrade() -> None:
    op.drop_table("modalidades")
    op.drop_table("eventos")

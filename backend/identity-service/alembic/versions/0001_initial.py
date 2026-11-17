"""Create identity accounts, role assignments and sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("accounts", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("password_hash", sa.String(512), nullable=False))
    op.create_table("role_assignments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False), sa.Column("role", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.UniqueConstraint("account_id", "role", name="uq_role_assignments_account_role"), sa.CheckConstraint("role IN ('cliente', 'organizador', 'administrador')", name="ck_role_type"), sa.CheckConstraint("status IN ('activo', 'pendiente', 'habilitado', 'deshabilitado')", name="ck_role_status"))
    op.create_table("sessions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked", sa.Boolean(), nullable=False), sa.CheckConstraint("expires_at > started_at AND expires_at <= started_at + interval '24 hours'", name="ck_session_expiry"))
    op.create_table("refresh_credentials", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id"), nullable=False), sa.Column("secret_hash", sa.String(64), nullable=False, unique=True), sa.Column("consumed", sa.Boolean(), nullable=False))
    op.create_index("uq_refresh_credentials_active_session", "refresh_credentials", ["session_id"], unique=True, postgresql_where=sa.text("consumed = false"))


def downgrade():
    op.drop_table("refresh_credentials")
    op.drop_table("sessions")
    op.drop_table("role_assignments")
    op.drop_table("accounts")

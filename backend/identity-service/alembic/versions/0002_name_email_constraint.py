"""Name the existing account email uniqueness constraint."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE accounts RENAME CONSTRAINT accounts_email_key TO uq_accounts_email")


def downgrade():
    op.execute("ALTER TABLE accounts RENAME CONSTRAINT uq_accounts_email TO accounts_email_key")

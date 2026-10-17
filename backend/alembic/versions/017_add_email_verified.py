# LogRaven — Migration: 017_add_email_verified
"""017 add email_verified to users

Adds the email_verified flag used by the email-verification flow. Existing
accounts are grandfathered in as verified so nobody is locked out.

Revision ID: 017
Revises: 016
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # New registrations set the flag explicitly; drop the permissive default.
    op.alter_column("users", "email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_verified")

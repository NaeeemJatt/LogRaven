"""019 add investigation queue timestamp

Revision ID: 019
Revises: 018
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investigations",
        sa.Column("queued_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        """
        UPDATE investigations
        SET queued_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        WHERE status IN ('queued', 'processing')
        """
    )
    op.create_index(
        "ix_investigations_status_queued_at",
        "investigations",
        ["status", "queued_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_investigations_status_queued_at", table_name="investigations")
    op.drop_column("investigations", "queued_at")

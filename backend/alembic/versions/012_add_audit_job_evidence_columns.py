# LogRaven — Migration: 012_add_audit_job_evidence_columns
"""012 add raw and sanitized evidence columns to soc2 audit jobs

Revision ID: 012
Revises: 011
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("raw_evidence", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("sanitized_evidence", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("soc2_audit_jobs", "sanitized_evidence")
    op.drop_column("soc2_audit_jobs", "raw_evidence")

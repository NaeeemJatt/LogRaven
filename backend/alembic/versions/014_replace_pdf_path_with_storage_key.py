# LogRaven — Migration: 014_replace_pdf_path_with_storage_key
"""014 replace pdf_path with pdf_storage_key on soc2_audit_jobs

Revision ID: 014
Revises: 013
Create Date: 2026-05-28

Replaces the raw filesystem path column (pdf_path) added in 013 with a
storage-abstraction key (pdf_storage_key) that works for both local and S3
backends — consistent with reports.pdf_storage_key.
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("pdf_storage_key", sa.String(500), nullable=True),
    )
    op.drop_column("soc2_audit_jobs", "pdf_path")


def downgrade() -> None:
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("pdf_path", sa.String(1000), nullable=True),
    )
    op.drop_column("soc2_audit_jobs", "pdf_storage_key")

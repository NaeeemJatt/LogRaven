# LogRaven — Migration: 013_add_audit_job_user_id_and_pdf_path
"""013 add user_id and pdf_path columns to soc2_audit_jobs

Revision ID: 013
Revises: 012
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_id — nullable so existing rows without an owner are not broken
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_soc2_audit_jobs_user_id", "soc2_audit_jobs", ["user_id"])
    op.create_foreign_key(
        "fk_soc2_audit_jobs_user_id",
        "soc2_audit_jobs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # pdf_path — stores the filesystem path of the cached SOC 2 PDF report
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("pdf_path", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("soc2_audit_jobs", "pdf_path")
    op.drop_constraint("fk_soc2_audit_jobs_user_id", "soc2_audit_jobs", type_="foreignkey")
    op.drop_index("ix_soc2_audit_jobs_user_id", table_name="soc2_audit_jobs")
    op.drop_column("soc2_audit_jobs", "user_id")

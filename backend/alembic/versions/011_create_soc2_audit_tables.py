# LogRaven — Migration: 011_create_soc2_audit_tables
"""011 create soc2 audit job and result tables

Revision ID: 011
Revises: 010
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "soc2_audit_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("role_arn", sa.String(1024), nullable=False),
        sa.Column("audit_start_date", sa.Date(), nullable=False),
        sa.Column("audit_end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_soc2_audit_jobs_status", "soc2_audit_jobs", ["status"])

    op.create_table(
        "soc2_audit_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "audit_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("soc2_audit_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("control_name", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("ai_description", sa.Text(), nullable=False),
        sa.Column("raw_evidence_summary", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_soc2_audit_results_audit_job_id", "soc2_audit_results", ["audit_job_id"])


def downgrade() -> None:
    op.drop_index("ix_soc2_audit_results_audit_job_id", table_name="soc2_audit_results")
    op.drop_table("soc2_audit_results")
    op.drop_index("ix_soc2_audit_jobs_status", table_name="soc2_audit_jobs")
    op.drop_table("soc2_audit_jobs")

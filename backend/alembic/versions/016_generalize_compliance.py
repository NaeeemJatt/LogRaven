# LogRaven — Migration: 016_generalize_compliance
"""016 generalize compliance to multi-framework

Adds multi-framework columns to the existing SOC 2 audit tables (additive, with
backward-compatible defaults so all existing rows remain valid), and creates the
compliance_snapshots table (evidence vault / posture trend).

Revision ID: 016
Revises: 015
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── AuditJob: multi-framework + monitoring columns ──────────────────────
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("frameworks", postgresql.JSONB(), nullable=False, server_default='["soc2"]'),
    )
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("evidence_signals", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("report_keys", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("recurrence", sa.String(length=20), nullable=False, server_default="none"),
    )
    op.add_column(
        "soc2_audit_jobs",
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_soc2_audit_jobs_next_run_at", "soc2_audit_jobs", ["next_run_at"])

    # ── AuditResult: framework column ───────────────────────────────────────
    op.add_column(
        "soc2_audit_results",
        sa.Column("framework", sa.String(length=40), nullable=False, server_default="soc2"),
    )
    op.create_index("ix_soc2_audit_results_framework", "soc2_audit_results", ["framework"])
    op.create_index(
        "ix_soc2_audit_results_job_framework",
        "soc2_audit_results",
        ["audit_job_id", "framework"],
    )

    # ── compliance_snapshots (evidence vault / trend) ───────────────────────
    op.create_table(
        "compliance_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("soc2_audit_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("framework", sa.String(length=40), nullable=False),
        sa.Column("score_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pass_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_delta", sa.Float(), nullable=True),
        sa.Column("evidence_signals", postgresql.JSONB(), nullable=True),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_snapshots_audit_job_id", "compliance_snapshots", ["audit_job_id"])
    op.create_index("ix_compliance_snapshots_framework", "compliance_snapshots", ["framework"])
    op.create_index("ix_compliance_snapshots_created_at", "compliance_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_compliance_snapshots_created_at", table_name="compliance_snapshots")
    op.drop_index("ix_compliance_snapshots_framework", table_name="compliance_snapshots")
    op.drop_index("ix_compliance_snapshots_audit_job_id", table_name="compliance_snapshots")
    op.drop_table("compliance_snapshots")

    op.drop_index("ix_soc2_audit_results_job_framework", table_name="soc2_audit_results")
    op.drop_index("ix_soc2_audit_results_framework", table_name="soc2_audit_results")
    op.drop_column("soc2_audit_results", "framework")

    op.drop_index("ix_soc2_audit_jobs_next_run_at", table_name="soc2_audit_jobs")
    op.drop_column("soc2_audit_jobs", "next_run_at")
    op.drop_column("soc2_audit_jobs", "recurrence")
    op.drop_column("soc2_audit_jobs", "report_keys")
    op.drop_column("soc2_audit_jobs", "evidence_signals")
    op.drop_column("soc2_audit_jobs", "frameworks")

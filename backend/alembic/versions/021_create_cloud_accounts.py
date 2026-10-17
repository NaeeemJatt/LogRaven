"""021 create cloud accounts table and link to audit jobs

Revision ID: 021
Revises: 020
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cloud_accounts ───────────────────────────────────────────────────────
    op.create_table(
        "cloud_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_cloud_accounts_user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="aws"),
        sa.Column("role_arn", sa.String(length=1024), nullable=False),
        sa.Column("account_id", sa.String(length=30), nullable=True),
        sa.Column(
            "default_frameworks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='["soc2"]',
        ),
        sa.Column("scan_schedule", sa.String(length=20), nullable=False, server_default="weekly"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("health_status", sa.String(length=30), nullable=False, server_default="unverified"),
        sa.Column("health_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cloud_accounts_user_id", "cloud_accounts", ["user_id"])
    op.create_index("ix_cloud_accounts_next_run_at", "cloud_accounts", ["next_run_at"])
    op.create_index("ix_cloud_accounts_health_status", "cloud_accounts", ["health_status"])

    # ── Link to soc2_audit_jobs ─────────────────────────────────────────────
    op.add_column(
        "soc2_audit_jobs",
        sa.Column(
            "cloud_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cloud_accounts.id", name="fk_soc2_audit_jobs_cloud_account_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_soc2_audit_jobs_cloud_account_id", "soc2_audit_jobs", ["cloud_account_id"])


def downgrade() -> None:
    op.drop_index("ix_soc2_audit_jobs_cloud_account_id", table_name="soc2_audit_jobs")
    op.drop_column("soc2_audit_jobs", "cloud_account_id")
    op.drop_index("ix_cloud_accounts_health_status", table_name="cloud_accounts")
    op.drop_index("ix_cloud_accounts_next_run_at", table_name="cloud_accounts")
    op.drop_index("ix_cloud_accounts_user_id", table_name="cloud_accounts")
    op.drop_table("cloud_accounts")

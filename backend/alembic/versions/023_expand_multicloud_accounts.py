"""023 expand cloud accounts for gcp and azure multi cloud fleet

Revision ID: 023
Revises: 022
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Allow role_arn to be nullable for non-AWS providers ───────────────────
    op.alter_column(
        "cloud_accounts",
        "role_arn",
        existing_type=sa.String(length=1024),
        nullable=True,
    )

    # ── GCP Columns ──────────────────────────────────────────────────────────
    op.add_column("cloud_accounts", sa.Column("gcp_project_id", sa.String(length=100), nullable=True))
    op.add_column("cloud_accounts", sa.Column("gcp_service_account_email", sa.String(length=255), nullable=True))
    op.add_column("cloud_accounts", sa.Column("gcp_workload_identity_pool", sa.String(length=255), nullable=True))

    # ── Azure Columns ────────────────────────────────────────────────────────
    op.add_column("cloud_accounts", sa.Column("azure_tenant_id", sa.String(length=100), nullable=True))
    op.add_column("cloud_accounts", sa.Column("azure_subscription_id", sa.String(length=100), nullable=True))
    op.add_column("cloud_accounts", sa.Column("azure_client_id", sa.String(length=100), nullable=True))

    # ── Index on provider for fast filtering across multi-cloud fleet ────────
    op.create_index("ix_cloud_accounts_provider", "cloud_accounts", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_cloud_accounts_provider", table_name="cloud_accounts")
    op.drop_column("cloud_accounts", "azure_client_id")
    op.drop_column("cloud_accounts", "azure_subscription_id")
    op.drop_column("cloud_accounts", "azure_tenant_id")
    op.drop_column("cloud_accounts", "gcp_workload_identity_pool")
    op.drop_column("cloud_accounts", "gcp_service_account_email")
    op.drop_column("cloud_accounts", "gcp_project_id")
    op.alter_column(
        "cloud_accounts",
        "role_arn",
        existing_type=sa.String(length=1024),
        nullable=False,
    )

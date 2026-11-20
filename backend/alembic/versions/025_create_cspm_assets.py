"""025 create cspm assets inventory table

Revision ID: 025
Revises: 024
Create Date: 2026-11-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cspm_assets",
        sa.Column("urn", sa.String(length=512), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=256), nullable=False),
        sa.Column("resource_name", sa.String(length=256), nullable=True),
        sa.Column("config_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("config_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "cloud_account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cloud_accounts.id", name="fk_cspm_assets_cloud_account_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tags", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("compliance_status", sa.String(length=32), nullable=False, server_default="UNASSESSED"),
        sa.Column("failing_rule_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passing_rule_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_cspm_assets_tenant_id", "cspm_assets", ["tenant_id"])
    op.create_index("idx_cspm_assets_tenant_provider", "cspm_assets", ["tenant_id", "provider"])
    op.create_index("idx_cspm_assets_tenant_service", "cspm_assets", ["tenant_id", "service"])
    op.create_index("idx_cspm_assets_account", "cspm_assets", ["account_id"])
    op.create_index("idx_cspm_assets_status", "cspm_assets", ["compliance_status"])
    op.create_index("idx_cspm_assets_config_sha", "cspm_assets", ["config_sha256"])


def downgrade() -> None:
    op.drop_index("idx_cspm_assets_config_sha", table_name="cspm_assets")
    op.drop_index("idx_cspm_assets_status", table_name="cspm_assets")
    op.drop_index("idx_cspm_assets_account", table_name="cspm_assets")
    op.drop_index("idx_cspm_assets_tenant_service", table_name="cspm_assets")
    op.drop_index("idx_cspm_assets_tenant_provider", table_name="cspm_assets")
    op.drop_index("ix_cspm_assets_tenant_id", table_name="cspm_assets")
    op.drop_table("cspm_assets")

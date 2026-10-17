"""022 create auditor access tokens table

Revision ID: 022
Revises: 021
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditor_access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_auditor_access_tokens_user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column(
            "cloud_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cloud_accounts.id", name="fk_auditor_access_tokens_cloud_account_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("passcode_hash", sa.String(length=128), nullable=True),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column(
            "allowed_frameworks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='["soc2", "iso27001"]',
        ),
        sa.Column("can_download_raw_evidence", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "ix_auditor_access_tokens_token_hash",
        "auditor_access_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_auditor_access_tokens_user_id",
        "auditor_access_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_auditor_access_tokens_company_name",
        "auditor_access_tokens",
        ["company_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_auditor_access_tokens_company_name", table_name="auditor_access_tokens")
    op.drop_index("ix_auditor_access_tokens_user_id", table_name="auditor_access_tokens")
    op.drop_index("ix_auditor_access_tokens_token_hash", table_name="auditor_access_tokens")
    op.drop_table("auditor_access_tokens")

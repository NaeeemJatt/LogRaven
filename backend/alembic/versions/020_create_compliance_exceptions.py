"""020 create compliance exceptions table and snapshot suppressed count

Revision ID: 020
Revises: 019
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── compliance_exceptions ───────────────────────────────────────────────
    op.create_table(
        "compliance_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_compliance_exceptions_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("framework", sa.String(length=40), nullable=False),
        sa.Column("control_id", sa.String(length=50), nullable=False),
        sa.Column("business_justification", sa.Text(), nullable=False),
        sa.Column("compensating_controls", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("suppressed_by", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_exceptions_user_id", "compliance_exceptions", ["user_id"])
    op.create_index("ix_compliance_exceptions_company_name", "compliance_exceptions", ["company_name"])
    op.create_index("ix_compliance_exceptions_framework", "compliance_exceptions", ["framework"])
    op.create_index("ix_compliance_exceptions_control_id", "compliance_exceptions", ["control_id"])
    op.create_index("ix_compliance_exceptions_status", "compliance_exceptions", ["status"])
    op.create_index(
        "ix_compliance_exceptions_lookup",
        "compliance_exceptions",
        ["company_name", "framework", "control_id", "status"],
    )

    # ── Add suppressed_count to compliance_snapshots ────────────────────────
    op.add_column(
        "compliance_snapshots",
        sa.Column("suppressed_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("compliance_snapshots", "suppressed_count")
    op.drop_index("ix_compliance_exceptions_lookup", table_name="compliance_exceptions")
    op.drop_index("ix_compliance_exceptions_status", table_name="compliance_exceptions")
    op.drop_index("ix_compliance_exceptions_control_id", table_name="compliance_exceptions")
    op.drop_index("ix_compliance_exceptions_framework", table_name="compliance_exceptions")
    op.drop_index("ix_compliance_exceptions_company_name", table_name="compliance_exceptions")
    op.drop_index("ix_compliance_exceptions_user_id", table_name="compliance_exceptions")
    op.drop_table("compliance_exceptions")

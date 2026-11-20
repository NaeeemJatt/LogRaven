"""024 create deterministic cspm catalogs and evaluation findings

Revision ID: 024
Revises: 023
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Controls Catalog Table ─────────────────────────────────────────────
    op.create_table(
        "cspm_controls_catalog",
        sa.Column("cid", sa.String(length=32), primary_key=True),
        sa.Column("control_name", sa.Text(), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("control_type", sa.String(length=64), nullable=False),
        sa.Column("execution_type", sa.String(length=32), nullable=False),
        sa.Column("criticality", sa.String(length=16), nullable=False),
        sa.Column("rule_spec_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("modified_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cspm_controls_service", "cspm_controls_catalog", ["service"])
    op.create_index("ix_cspm_controls_platform", "cspm_controls_catalog", ["platform"])

    # ── 2. Policies Catalog Table ─────────────────────────────────────────────
    op.create_table(
        "cspm_policies_catalog",
        sa.Column("policy_title", sa.String(length=255), primary_key=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("execution_type", sa.String(length=32), nullable=False),
        sa.Column("mapped_cids", ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("modified_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cspm_policies_provider", "cspm_policies_catalog", ["provider"])

    # ── 3. Mandates Catalog Table ─────────────────────────────────────────────
    op.create_table(
        "cspm_mandates_catalog",
        sa.Column("mandate_name", sa.String(length=255), primary_key=True),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("mapped_cids", ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_modified_date", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 4. Evaluation Findings Table ──────────────────────────────────────────
    op.create_table(
        "cspm_evaluation_findings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column(
            "cid",
            sa.String(length=32),
            sa.ForeignKey("cspm_controls_catalog.cid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_urn", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("criticality", sa.String(length=16), nullable=False),
        sa.Column("evidence_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "cid", "resource_urn", name="uq_cspm_findings_tenant_cid_urn"),
        sa.CheckConstraint("status IN ('PASS', 'FAIL')", name="ck_cspm_findings_status"),
    )
    op.create_index("ix_cspm_findings_tenant_id", "cspm_evaluation_findings", ["tenant_id"])
    op.create_index("ix_cspm_findings_cid", "cspm_evaluation_findings", ["cid"])
    op.create_index(
        "idx_findings_tenant_status",
        "cspm_evaluation_findings",
        ["tenant_id", "status", "criticality"],
    )

    # ── 5. Heartbeat Tracking for Zombie Reapers ──────────────────────────────
    op.add_column("investigations", sa.Column("heartbeat_at", sa.DateTime(), nullable=True))
    op.add_column("soc2_audit_jobs", sa.Column("heartbeat_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("soc2_audit_jobs", "heartbeat_at")
    op.drop_column("investigations", "heartbeat_at")

    op.drop_index("idx_findings_tenant_status", table_name="cspm_evaluation_findings")
    op.drop_index("ix_cspm_findings_cid", table_name="cspm_evaluation_findings")
    op.drop_index("ix_cspm_findings_tenant_id", table_name="cspm_evaluation_findings")
    op.drop_table("cspm_evaluation_findings")

    op.drop_table("cspm_mandates_catalog")

    op.drop_index("ix_cspm_policies_provider", table_name="cspm_policies_catalog")
    op.drop_table("cspm_policies_catalog")

    op.drop_index("ix_cspm_controls_platform", table_name="cspm_controls_catalog")
    op.drop_index("ix_cspm_controls_service", table_name="cspm_controls_catalog")
    op.drop_table("cspm_controls_catalog")

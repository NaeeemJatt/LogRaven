# LogRaven — Migration: 005_create_findings
"""005 create findings

Revision ID: 005
Revises: 004
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'findings',
        sa.Column('id',                   postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('report_id',            postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('severity',             sa.String(20),   nullable=False),
        sa.Column('title',                sa.String(300),  nullable=False),
        sa.Column('description',          sa.Text(),       nullable=False),
        sa.Column('mitre_technique_id',   sa.String(20),   nullable=True),
        sa.Column('mitre_technique_name', sa.String(200),  nullable=True),
        sa.Column('mitre_tactic',         sa.String(100),  nullable=True),
        sa.Column('iocs',                 postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('remediation',          sa.Text(),       nullable=True),
        sa.Column('source_files',         postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('finding_type',         sa.String(20),   nullable=False, server_default='single'),
        sa.Column('confidence',           sa.Float(),      nullable=False, server_default='0.8'),
        sa.Column('created_at',           sa.DateTime(),   nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_findings_report_id', 'findings', ['report_id'])


def downgrade() -> None:
    op.drop_index('ix_findings_report_id', table_name='findings')
    op.drop_table('findings')

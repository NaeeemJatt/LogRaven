# LogRaven — Migration: 004_create_reports
"""004 create reports

Revision ID: 004
Revises: 003
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reports',
        sa.Column('id',                     postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('investigation_id',        postgresql.UUID(as_uuid=True), sa.ForeignKey('investigations.id'), nullable=False),
        sa.Column('user_id',                 postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('summary',                 sa.Text(),    nullable=True),
        sa.Column('severity_counts',         postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('correlated_findings',     postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('single_source_findings',  postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('mitre_techniques',        postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('pdf_storage_key',         sa.String(500), nullable=True),
        sa.Column('created_at',              sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('investigation_id', name='uq_reports_investigation_id'),
    )
    op.create_index('ix_reports_user_id', 'reports', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_reports_user_id', table_name='reports')
    op.drop_table('reports')

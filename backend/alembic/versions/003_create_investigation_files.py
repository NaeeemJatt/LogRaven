# LogRaven — Migration: 003_create_investigation_files
"""003 create investigation files

Revision ID: 003
Revises: 002
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'investigation_files',
        sa.Column('id',               postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('investigation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('investigations.id'), nullable=False),
        sa.Column('filename',         sa.String(255),  nullable=False),
        sa.Column('source_type',      sa.String(50),   nullable=False),
        sa.Column('log_type',         sa.String(20),   nullable=True),
        sa.Column('storage_key',      sa.String(500),  nullable=False),
        sa.Column('status',           sa.String(20),   nullable=False, server_default='pending'),
        sa.Column('event_count',      sa.Integer(),    nullable=True),
        sa.Column('error_message',    sa.Text(),       nullable=True),
        sa.Column('uploaded_at',      sa.DateTime(),   nullable=False, server_default=sa.text('now()')),
        sa.Column('parsed_at',        sa.DateTime(),   nullable=True),
    )
    op.create_index('ix_investigation_files_investigation_id', 'investigation_files', ['investigation_id'])


def downgrade() -> None:
    op.drop_index('ix_investigation_files_investigation_id', table_name='investigation_files')
    op.drop_table('investigation_files')

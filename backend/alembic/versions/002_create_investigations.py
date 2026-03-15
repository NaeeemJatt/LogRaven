# LogRaven — Migration: 002_create_investigations
"""002 create investigations

Revision ID: 002
Revises: 001
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'investigations',
        sa.Column('id',                  postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id',             postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name',                sa.String(200), nullable=False),
        sa.Column('status',              sa.String(20),  nullable=False, server_default='draft'),
        sa.Column('correlation_enabled', sa.Boolean(),   nullable=False, server_default=sa.text('true')),
        sa.Column('time_window_start',   sa.DateTime(),  nullable=True),
        sa.Column('time_window_end',     sa.DateTime(),  nullable=True),
        sa.Column('created_at',          sa.DateTime(),  nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at',        sa.DateTime(),  nullable=True),
    )
    op.create_index('ix_investigations_user_id', 'investigations', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_investigations_user_id', table_name='investigations')
    op.drop_table('investigations')

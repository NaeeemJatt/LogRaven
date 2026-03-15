# LogRaven — Migration: 006_create_audit_log
"""006 create audit log

Revision ID: 006
Revises: 005
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id',         postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id',    postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action',     sa.String(50),   nullable=False),
        sa.Column('ip_address', sa.String(45),   nullable=True),
        sa.Column('user_agent', sa.String(500),  nullable=True),
        sa.Column('metadata',   postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(),   nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_user_id', table_name='audit_log')
    op.drop_table('audit_log')

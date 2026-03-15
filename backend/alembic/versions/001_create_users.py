# LogRaven — Migration: 001_create_users
"""001 create users

Revision ID: 001
Revises:
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id',            postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email',         sa.String(255),  nullable=False),
        sa.Column('password_hash', sa.String(255),  nullable=False),
        sa.Column('tier',          sa.String(20),   nullable=False, server_default='free'),
        sa.Column('created_at',    sa.DateTime(),   nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at',    sa.DateTime(),   nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

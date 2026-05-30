# LogRaven — Migration: 015_add_user_name_timezone
"""015 add user name and timezone

Revision ID: 015
Revises: 014
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('name',     sa.String(120), nullable=True))
    op.add_column('users', sa.Column('timezone', sa.String(64),  nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'name')

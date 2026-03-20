# LogRaven — Migration: 007_add_investigation_error_message
"""007 add investigation error message

Revision ID: 007
Revises: 006
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'investigations',
        sa.Column('error_message', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('investigations', 'error_message')

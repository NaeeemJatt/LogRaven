# LogRaven — Migration: 008_add_investigation_progress_stage
"""008 add investigation progress_stage

Revision ID: 008
Revises: 007
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'investigations',
        sa.Column('progress_stage', sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('investigations', 'progress_stage')

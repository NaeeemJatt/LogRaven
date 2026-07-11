# LogRaven — Migration: 018_drop_investigation_time_window
"""018 drop unused investigation time-window columns

time_window_start / time_window_end were created in 002 but never exposed by
any API or used by the pipeline (correlation windows are computed internally).
Dropping them keeps the schema honest. Both are nullable and always NULL, so
this is data-loss-free in practice.

Revision ID: 018
Revises: 017
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("investigations", "time_window_start")
    op.drop_column("investigations", "time_window_end")


def downgrade() -> None:
    op.add_column("investigations", sa.Column("time_window_start", sa.DateTime(), nullable=True))
    op.add_column("investigations", sa.Column("time_window_end", sa.DateTime(), nullable=True))

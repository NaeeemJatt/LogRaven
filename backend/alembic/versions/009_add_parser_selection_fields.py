# LogRaven — Migration: 009_add_parser_selection_fields
"""009 add parser detection confidence and selection detail

Revision ID: 009
Revises: 008
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investigation_files",
        sa.Column("parser_detection_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "investigation_files",
        sa.Column("parser_selection_detail", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("investigation_files", "parser_selection_detail")
    op.drop_column("investigation_files", "parser_detection_confidence")

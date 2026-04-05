# LogRaven — Migration: 010_add_ingestion_mode
"""010 add investigation_files.ingestion_mode (parsers | decoders)

Revision ID: 010
Revises: 009
Create Date: 2026-04-03
"""
from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investigation_files",
        sa.Column(
            "ingestion_mode",
            sa.String(length=20),
            nullable=False,
            server_default="parsers",
        ),
    )


def downgrade() -> None:
    op.drop_column("investigation_files", "ingestion_mode")

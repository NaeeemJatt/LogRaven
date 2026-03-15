# LogRaven — Report Model
#
# PURPOSE:
#   Stores the complete output of a LogRaven analysis.
#   JSONB columns allow efficient querying of nested finding data.
#
# TWO FINDING COLUMNS:
#   correlated_findings    — cross-source chains (highest priority findings)
#   single_source_findings — individual file findings (lower priority)
#
# PDF:
#   pdf_storage_key points to lograven-report-{uuid}.pdf in local/reports/
#
# TODO Month 4 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    id:                      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id:        Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("investigations.id"), unique=True, nullable=False)
    user_id:                 Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    summary:                 Mapped[str | None]   = mapped_column(Text, nullable=True)
    severity_counts:         Mapped[dict]         = mapped_column(JSONB, default=dict)
    correlated_findings:     Mapped[list]         = mapped_column(JSONB, default=list)
    single_source_findings:  Mapped[list]         = mapped_column(JSONB, default=list)
    mitre_techniques:        Mapped[list]         = mapped_column(JSONB, default=list)
    pdf_storage_key:         Mapped[str | None]   = mapped_column(String(500), nullable=True)
    created_at:              Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)

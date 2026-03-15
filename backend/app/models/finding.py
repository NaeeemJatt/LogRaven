# LogRaven — Finding Model
#
# PURPOSE:
#   One row per individual finding in a report.
#   Storing findings separately enables cross-report analytics.
#
# FINDING_TYPE VALUES:
#   correlated — found by correlation engine (spans multiple source files)
#   single     — found in a single log file
#
# SOURCE_FILES:
#   JSON array of investigation_file IDs that contributed to this finding.
#   For correlated findings: 2+ file IDs.
#   For single findings: 1 file ID.
#
# TODO Month 4 Week 1: Implement this model.

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.report import Report


class Finding(Base):
    __tablename__ = "findings"

    id:                   Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id:            Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True)
    severity:             Mapped[str]         = mapped_column(String(20), nullable=False)
    title:                Mapped[str]         = mapped_column(String(300), nullable=False)
    description:          Mapped[str]         = mapped_column(Text, nullable=False)
    mitre_technique_id:   Mapped[str | None]  = mapped_column(String(20), nullable=True)
    mitre_technique_name: Mapped[str | None]  = mapped_column(String(200), nullable=True)
    mitre_tactic:         Mapped[str | None]  = mapped_column(String(100), nullable=True)
    iocs:                 Mapped[list]        = mapped_column(JSONB, default=list)
    remediation:          Mapped[str | None]  = mapped_column(Text, nullable=True)
    source_files:         Mapped[list]        = mapped_column(JSONB, default=list)
    finding_type:         Mapped[str]         = mapped_column(String(20), nullable=False, default="single")
    confidence:           Mapped[float]       = mapped_column(Float, default=0.8)
    created_at:           Mapped[datetime]    = mapped_column(DateTime, default=datetime.utcnow)

    report: Mapped["Report"] = relationship("Report", back_populates="findings")

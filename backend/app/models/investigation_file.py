# LogRaven — InvestigationFile Model
#
# PURPOSE:
#   One row per uploaded file in an investigation.
#   Files parse independently — one failure does not block others.
#   The source_type field drives correlation entity extraction.
#
# SOURCE_TYPE VALUES:
#   windows_endpoint | linux_endpoint | firewall | network | web_server | cloudtrail
#
# LOG_TYPE VALUES (auto-detected by detector.py):
#   evtx | syslog | cloudtrail | nginx
#
# STORAGE KEY FORMAT:
#   uploads/{investigation_id}/{uuid}_{original_filename}
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.investigation import Investigation


class InvestigationFile(Base):
    __tablename__ = "investigation_files"

    id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=False, index=True)
    filename:         Mapped[str]             = mapped_column(String(255), nullable=False)
    source_type:      Mapped[str]             = mapped_column(String(50), nullable=False)
    log_type:         Mapped[str | None]      = mapped_column(String(20), nullable=True)
    storage_key:      Mapped[str]             = mapped_column(String(500), nullable=False)
    status:           Mapped[str]             = mapped_column(String(20), nullable=False, default="pending")
    event_count:      Mapped[int | None]      = mapped_column(Integer, nullable=True)
    error_message:    Mapped[str | None]      = mapped_column(Text, nullable=True)
    uploaded_at:      Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)
    parsed_at:        Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="files")

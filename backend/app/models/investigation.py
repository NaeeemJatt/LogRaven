# LogRaven — Investigation Model
#
# PURPOSE:
#   An investigation is a named container for one or more log files.
#   This is the core LogRaven unit of work.
#
# STATUS FLOW:
#   draft -> queued -> processing -> complete / failed
#
# CORRELATION:
#   correlation_enabled=True means the correlation engine will run
#   when 2+ files with different source_types are uploaded.
#   Single file investigations always work regardless of this flag.
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.investigation_file import InvestigationFile
    from app.models.report import Report


class Investigation(Base):
    __tablename__ = "investigations"

    id:                  Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:             Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name:                Mapped[str]               = mapped_column(String(200), nullable=False)
    status:              Mapped[str]               = mapped_column(String(20), nullable=False, default="draft")
    correlation_enabled: Mapped[bool]              = mapped_column(Boolean, default=True)
    time_window_start:   Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)
    time_window_end:     Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)
    created_at:          Mapped[datetime]          = mapped_column(DateTime, default=datetime.utcnow)
    completed_at:        Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)
    error_message:       Mapped[str | None]        = mapped_column(Text, nullable=True)

    user:   Mapped["User"]                       = relationship("User",              back_populates="investigations")
    files:  Mapped[list["InvestigationFile"]]    = relationship("InvestigationFile", back_populates="investigation", cascade="all, delete-orphan")
    report: Mapped["Report | None"]             = relationship("Report",            back_populates="investigation", uselist=False)

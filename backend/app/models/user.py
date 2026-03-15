# LogRaven — User Model
#
# PURPOSE:
#   Represents a LogRaven user account.
#   The `tier` field drives all business logic:
#     - Upload file size limits (free=5MB, pro=50MB, team=200MB)
#     - AI cost ceiling (free=2k, pro=10k, team=50k events)
#     - Report retention period
#
# RELATIONSHIPS:
#   investigations — one-to-many
#   audit_log      — one-to-many
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.investigation import Investigation
    from app.models.audit import AuditLog


class User(Base):
    __tablename__ = "users"

    id:            Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:         Mapped[str]        = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str]        = mapped_column(String(255), nullable=False)
    tier:          Mapped[str]        = mapped_column(String(20), nullable=False, default="free")
    created_at:    Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:    Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    investigations: Mapped[list["Investigation"]] = relationship("Investigation", back_populates="user", lazy="select")
    audit_logs:     Mapped[list["AuditLog"]]      = relationship("AuditLog",      back_populates="user", lazy="select")

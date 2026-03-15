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
from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id:            Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:         Mapped[str]        = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str]        = mapped_column(String(255), nullable=False)
    tier:          Mapped[str]        = mapped_column(String(20), nullable=False, default="free")
    created_at:    Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:    Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # TODO: Add investigations relationship
    # TODO: Add audit_log relationship

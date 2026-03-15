# LogRaven — AuditLog Model
#
# PURPOSE:
#   Security audit trail for the LogRaven platform.
#   Records every meaningful user action with IP and metadata.
#
# IMPORTANT: Insert-only table.
#   Records are NEVER updated or deleted.
#   1-year retention policy.
#   Used for security investigations and compliance documentation.
#
# ACTION VALUES:
#   login | register | upload | analyze | report_view | download | failed_login
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id:         Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action:     Mapped[str]             = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None]      = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None]      = mapped_column(String(500), nullable=True)
    metadata_:  Mapped[dict]            = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)

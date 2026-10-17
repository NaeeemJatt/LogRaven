# LogRaven — AuditLog Model
#
# PURPOSE:
#   Security audit trail for the LogRaven platform.
#   Records every meaningful user action with IP and metadata.
#
# IMPORTANT: Insert-only table.
#   Records are never updated in place. A daily maintenance task
#   (maintenance.purge_expired_audit_logs) deletes rows older than the
#   1-year retention policy; nothing else deletes them.
#   Used for security investigations and compliance documentation.
#
# ACTION VALUES:
#   login | register | failed_login | email_verified
#   password_changed | password_reset_requested | password_reset
#   account_deleted | tier_change
#   investigation_created | investigation_deleted | upload | file_deleted
#   analyze | report_view | download
#   compliance_audit_started | compliance_audit_shared
#   compliance_report_downloaded | compliance_evidence_downloaded
#

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_log"

    id:         Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action:     Mapped[str]             = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None]      = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None]      = mapped_column(String(500), nullable=True)
    metadata_:  Mapped[dict]            = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")

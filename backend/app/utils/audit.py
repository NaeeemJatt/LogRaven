# LogRaven — Audit-trail helper
#
# Queues an AuditLog row on the caller's session; it is persisted by the
# caller's commit so the audit row and the action it records share one
# transaction.

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def add_audit(
    db: AsyncSession,
    *,
    user_id,
    action: str,
    request: Request | None,
    metadata: dict,
) -> None:
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.client.host if request is not None and request.client else None,
        user_agent=request.headers.get("user-agent") if request is not None else None,
        metadata_=metadata,
    ))

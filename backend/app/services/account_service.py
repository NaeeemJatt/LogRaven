# LogRaven — Account lifecycle service
#
# Email verification, password reset, and full account deletion
# (DB rows + storage blobs). Route handlers stay thin.

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
from app.models.investigation import Investigation
from app.models.report import Report
from app.models.soc2_audit import AuditJob
from app.models.user import User
from app.services import email_service
from app.utils import security
from app.utils.logger import get_logger
from app.utils.storage import create_storage_backend

logger = get_logger(__name__)


# ── Email verification ───────────────────────────────────────────────────────

async def send_verification(user: User) -> None:
    if user.email_verified:
        return
    token = security.create_email_verify_token(str(user.id), user.email)
    await email_service.send_verification_email(user.email, token)


async def confirm_verification(token: str, db: AsyncSession) -> None:
    user_id, email = security.decode_email_verify_token(token)
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or user.email != email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification link")
    if not user.email_verified:
        user.email_verified = True
        user.updated_at = datetime.utcnow()
        db.add(AuditLog(user_id=user.id, action="email_verified", metadata_={}))
        await db.commit()


# ── Password reset ───────────────────────────────────────────────────────────

async def request_password_reset(email: str, db: AsyncSession, ip_address: str | None = None) -> None:
    """Always succeeds from the caller's perspective (no user enumeration)."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        logger.info("[password-reset] requested for unknown email")
        return
    token = security.create_password_reset_token(str(user.id), user.password_hash)
    await email_service.send_password_reset_email(user.email, token)
    db.add(AuditLog(
        user_id=user.id,
        action="password_reset_requested",
        ip_address=ip_address,
        metadata_={},
    ))
    await db.commit()


async def reset_password(token: str, new_password: str, db: AsyncSession, ip_address: str | None = None) -> None:
    if len(new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    # Peek at the (unverified) subject to locate the user, then validate the
    # token fully — signature, expiry, audience, and single-use fingerprint —
    # against that user's current password hash.
    import jwt as _jwt

    try:
        unverified = _jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset link")

    sub = unverified.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset link")
    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset link")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset link")

    # Full validation: signature, expiry, audience, single-use fingerprint.
    security.decode_password_reset_token(token, user.password_hash)

    user.password_hash = security.hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.add(AuditLog(user_id=user.id, action="password_reset", ip_address=ip_address, metadata_={}))
    await db.commit()


# ── Account deletion ─────────────────────────────────────────────────────────

async def delete_account(user: User, password: str, db: AsyncSession, ip_address: str | None = None) -> None:
    """Verify password, purge storage blobs, delete owned rows, delete the user."""
    if not security.verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")

    storage = create_storage_backend()

    async def _delete_blob(key: str | None) -> None:
        if not key:
            return
        try:
            await storage.delete_file(key)
        except Exception as exc:  # storage cleanup is best-effort
            logger.warning("[account-delete] blob cleanup failed | key=%s | %s", key, exc)

    # Investigations: uploaded files + report PDFs, then rows (cascade covers children).
    inv_result = await db.execute(
        select(Investigation)
        .options(selectinload(Investigation.files), selectinload(Investigation.report))
        .where(Investigation.user_id == user.id)
    )
    investigations = list(inv_result.scalars().all())
    for inv in investigations:
        for f in inv.files:
            await _delete_blob(f.storage_key)
        if inv.report:
            await _delete_blob(inv.report.pdf_storage_key)
        await db.delete(inv)

    # Orphan-safe: reports owned by the user but not reached via investigations.
    rep_result = await db.execute(select(Report).where(Report.user_id == user.id))
    for report in rep_result.scalars().all():
        await _delete_blob(report.pdf_storage_key)
        await db.delete(report)

    # Compliance audit jobs: per-framework PDFs + legacy PDF key, then rows
    # (results/snapshots cascade at DB level).
    job_result = await db.execute(select(AuditJob).where(AuditJob.user_id == user.id))
    for job in job_result.scalars().all():
        await _delete_blob(job.pdf_storage_key)
        for key in (job.report_keys or {}).values():
            await _delete_blob(key)
        await db.delete(job)

    # Keep the security audit trail but detach it from the deleted user.
    await db.execute(
        update(AuditLog).where(AuditLog.user_id == user.id).values(user_id=None)
    )
    db.add(AuditLog(
        action="account_deleted",
        ip_address=ip_address,
        metadata_={"email": user.email},
    ))

    await db.delete(user)
    await db.commit()
    logger.info("[account-delete] account removed | investigations=%d", len(investigations))

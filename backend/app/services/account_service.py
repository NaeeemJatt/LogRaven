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

def _mask_email(email: str) -> str:
    """Mask email for pre-flight display: e.g. u***@domain.com."""
    if "@" not in email:
        return "u***@domain.com"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = f"{local}***"
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


async def request_password_reset(email: str, db: AsyncSession, ip_address: str | None = None) -> None:
    """Always succeeds from the caller's perspective (zero-knowledge anti-enumeration)."""
    import asyncio
    import hashlib
    import redis.asyncio as aioredis
    from app.config import settings

    clean_email = email.lower().strip()
    email_hash = hashlib.sha256(clean_email.encode("utf-8")).hexdigest()
    cooldown_key = f"lograven:pwd_reset_cooldown:{email_hash}"

    # Check / set per-email cooldown lock (60 seconds) in Redis
    cooldown_active = False
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        # Attempt to acquire 60-second cooldown lock
        acquired = await client.set(cooldown_key, "1", ex=60, nx=True)
        await client.aclose()
        if not acquired:
            cooldown_active = True
    except Exception:
        pass

    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()

    if user is None:
        # Equalize execution timing side-channel
        security.verify_password("dummy-timing-sync", security.DUMMY_PASSWORD_HASH)
        await asyncio.sleep(0.18)  # simulate SMTP dispatch latency
        logger.info("[password-reset] requested for unknown email (timing equalized)")
        return

    if cooldown_active:
        logger.info("[password-reset] cooldown active for user=%s; duplicate email suppressed", user.id)
        return

    token = security.create_password_reset_token(str(user.id), user.password_hash)
    await email_service.send_password_reset_email(user.email, token)
    db.add(AuditLog(
        user_id=user.id,
        action="password_reset_requested",
        ip_address=ip_address,
        metadata_={"method": "email"},
    ))
    await db.commit()


async def verify_reset_token(token: str, db: AsyncSession) -> dict:
    """
    Idempotent pre-flight token verification.
    Validates signature, expiry, audience, and single-use fingerprint without consuming the token.
    Returns masked email or raises HTTPException(400).
    """
    import jwt as _jwt

    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_INVALID", "message": "Reset token is required"},
        )

    try:
        unverified = _jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_INVALID", "message": "Invalid or malformed reset link"},
        )

    sub = unverified.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_INVALID", "message": "Invalid reset link claims"},
        )
    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_INVALID", "message": "Invalid reset link claims"},
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_INVALID", "message": "Invalid reset link"},
        )

    # Full verification: signature, expiry, audience, single-use pwf
    try:
        security.decode_password_reset_token_full(token, user.password_hash)
    except HTTPException as exc:
        code = "TOKEN_EXPIRED" if "expired" in str(exc.detail).lower() else "TOKEN_ALREADY_USED"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": code, "message": str(exc.detail)},
        ) from exc

    return {
        "valid": True,
        "email_masked": _mask_email(user.email),
    }


async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    from app.services import auth_service
    from app.utils.password_policy import validate_password_complexity
    import redis.asyncio as aioredis
    from app.config import settings
    import jwt as _jwt

    # 1. Parse unverified claims to locate user
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

    # 2. Acquire atomic database row lock inside transaction
    result = await db.execute(select(User).where(User.id == user_uuid).with_for_update())
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset link")

    # 3. Enforce enterprise password policy (NIST SP 800-63B)
    validate_password_complexity(new_password, user.email)

    # 4. Full token validation (signature, expiry, audience, single-use fingerprint)
    payload = security.decode_password_reset_token_full(token, user.password_hash)
    jti = payload.get("jti")

    # 5. Atomic Redis concurrency lock on JTI
    if jti:
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            lock_acquired = await client.set(f"lograven:lock:reset_token:{jti}", "1", ex=30, nx=True)
            await client.aclose()
            if not lock_acquired:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Password reset is already processing for this token",
                )
        except HTTPException:
            raise
        except Exception:
            pass

    # 6. Update user password hash
    user.password_hash = security.hash_password(new_password)
    user.updated_at = datetime.utcnow()

    # 7. Global session revocation across all devices
    await auth_service.revoke_all_user_tokens(user.id)

    # 8. Record audit trail
    db.add(AuditLog(
        user_id=user.id,
        action="password_reset_success",
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_={"method": "token_reset"},
    ))
    await db.commit()

    # 9. Send immediate security alert email
    try:
        await email_service.send_password_reset_confirmation_email(user.email, ip_address, user_agent)
    except Exception as exc:
        logger.warning("[password-reset] Confirmation email failed: %s", exc)


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

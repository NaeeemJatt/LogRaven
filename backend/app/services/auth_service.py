# LogRaven — Auth Service
#
# PURPOSE:
#   Business logic for user authentication.
#   Route handlers call these functions — no DB access in routes.

import uuid
import asyncio

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.user import TokenResponse, UserResponse
from app.utils import refresh_tokens
from app.utils import security


async def _wait_for_refresh_result(jti: str, user_id: str, *, attempts: int = 10, delay: float = 0.1) -> dict | None:
    for _ in range(attempts):
        result = await refresh_tokens.get_refresh_result(jti, user_id)
        if result is not None:
            return result
        await asyncio.sleep(delay)
    return None


async def register_user(
    email: str,
    password: str,
    db: AsyncSession,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenResponse:
    # Check email length and format
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    generic_register_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to register with those credentials",
    )

    # Check email not already taken
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        db.add(AuditLog(
            action="failed_register",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_={"email": email, "reason": "already_registered"},
        ))
        await db.commit()
        raise generic_register_exc

    # Create user
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=security.hash_password(password),
        tier="free",
    )
    db.add(user)
    await db.flush()  # populate user.id before audit log

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="register",
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_={},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    refresh_token, refresh_jti = security.create_refresh_token(str(user.id))
    await refresh_tokens.store_refresh_token(refresh_jti, str(user.id))
    return TokenResponse(
        access_token=security.create_access_token(str(user.id), user.tier),
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


async def login_user(
    email: str,
    password: str,
    db: AsyncSession,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenResponse:
    # Fetch user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Use same error message for both "not found" and "wrong password"
    # to prevent user enumeration
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        # Still write failed_login audit (no user_id)
        db.add(AuditLog(
            action="failed_login",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_={"email": email, "reason": "user_not_found"},
        ))
        await db.commit()
        raise invalid_exc

    if not security.verify_password(password, user.password_hash):
        db.add(AuditLog(
            user_id=user.id,
            action="failed_login",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_={"reason": "wrong_password"},
        ))
        await db.commit()
        raise invalid_exc

    # Success — audit log
    db.add(AuditLog(
        user_id=user.id,
        action="login",
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_={},
    ))
    await db.commit()

    refresh_token, refresh_jti = security.create_refresh_token(str(user.id))
    await refresh_tokens.store_refresh_token(refresh_jti, str(user.id))
    return TokenResponse(
        access_token=security.create_access_token(str(user.id), user.tier),
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


async def refresh_token(token: str, db: AsyncSession) -> dict:
    # decode_token raises HTTP 401 on any failure
    payload = security.decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )
    try:
        canonical_user_id = str(uuid.UUID(user_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    jti: str | None = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(canonical_user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    cached_result = await refresh_tokens.get_refresh_result(jti, canonical_user_id)
    if cached_result is not None:
        return cached_result

    lock_acquired = False
    try:
        for _ in range(10):
            lock_acquired = await refresh_tokens.acquire_refresh_lock(jti)
            if lock_acquired:
                break

            cached_result = await refresh_tokens.get_refresh_result(jti, canonical_user_id)
            if cached_result is not None:
                return cached_result

            await asyncio.sleep(0.1)

        if not lock_acquired:
            cached_result = await _wait_for_refresh_result(jti, canonical_user_id)
            if cached_result is not None:
                return cached_result
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Refresh already in progress",
            )

        cached_result = await refresh_tokens.get_refresh_result(jti, canonical_user_id)
        if cached_result is not None:
            return cached_result

        if not await refresh_tokens.consume_refresh_token(jti, canonical_user_id):
            cached_result = await refresh_tokens.get_refresh_result(jti, canonical_user_id)
            if cached_result is not None:
                return cached_result
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or already used",
            )

        new_refresh_token, new_refresh_jti = security.create_refresh_token(str(user.id))
        access_token = security.create_access_token(str(user.id), user.tier)
        await refresh_tokens.store_refresh_rotation_result(
            jti,
            canonical_user_id,
            new_refresh_jti,
            access_token,
            new_refresh_token,
        )
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        }
    finally:
        if lock_acquired:
            await refresh_tokens.release_refresh_lock(jti)

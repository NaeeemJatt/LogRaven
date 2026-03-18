# LogRaven — Auth Service
#
# PURPOSE:
#   Business logic for user authentication.
#   Route handlers call these functions — no DB access in routes.

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.user import TokenResponse
from app.utils import security


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

    # Check email not already taken
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

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

    return TokenResponse(
        access_token=security.create_access_token(str(user.id), user.tier),
        refresh_token=security.create_refresh_token(str(user.id)),
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

    return TokenResponse(
        access_token=security.create_access_token(str(user.id), user.tier),
        refresh_token=security.create_refresh_token(str(user.id)),
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

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return {
        "access_token": security.create_access_token(str(user.id), user.tier),
        "token_type": "bearer",
    }

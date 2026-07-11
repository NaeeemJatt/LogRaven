# LogRaven — Auth Routes
#
# HTTP handlers; business logic in services/auth_service.py.
# httpOnly cookies for browsers; JSON tokens optional (INCLUDE_TOKENS_IN_AUTH_JSON).

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.schemas.user import (
    AuthSessionResponse,
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserCreate,
    UserLogin,
    UserResponse,
    VerifyEmailRequest,
)
from app.services import account_service, auth_service
from app.utils.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.utils.refresh_tokens import revoke_refresh_token
from app.utils.security import decode_token


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


router = APIRouter()


def _session_payload(access: str | None, refresh: str | None, user: UserResponse | dict | None = None) -> AuthSessionResponse:
    if settings.INCLUDE_TOKENS_IN_AUTH_JSON:
        return AuthSessionResponse(
            token_type="bearer",
            access_token=access,
            refresh_token=refresh,
            user=user,
        )
    return AuthSessionResponse(token_type="bearer", user=user)


@router.post("/register", response_model=AuthSessionResponse, response_model_exclude_none=True, status_code=201)
@limiter.limit("10/minute")
async def register(
    request: Request,
    response: Response,
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    tokens = await auth_service.register_user(
        email=body.email,
        password=body.password,
        db=db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return _session_payload(tokens.access_token, tokens.refresh_token, tokens.user)


@router.post("/login", response_model=AuthSessionResponse, response_model_exclude_none=True)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    tokens = await auth_service.login_user(
        email=body.email,
        password=body.password,
        db=db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return _session_payload(tokens.access_token, tokens.refresh_token, tokens.user)


@router.post("/refresh", response_model=AuthSessionResponse, response_model_exclude_none=True)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    body: RefreshRequest = Body(default_factory=RefreshRequest),
) -> AuthSessionResponse:
    raw = body.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await auth_service.refresh_token(token=raw, db=db)
    set_auth_cookies(response, result["access_token"], result["refresh_token"])
    return _session_payload(result["access_token"], result["refresh_token"], result.get("user"))


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        try:
            payload = decode_token(raw)
            if payload.get("type") == "refresh" and payload.get("jti"):
                await revoke_refresh_token(payload["jti"])
        except HTTPException:
            pass
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)) -> UserResponse:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update display name and/or timezone for the authenticated user."""
    from datetime import datetime

    if body.name is not None:
        name = body.name.strip()
        if len(name) > 120:
            raise HTTPException(status_code=400, detail="name must be 120 characters or fewer")
        current_user.name = name or None

    if body.timezone is not None:
        current_user.timezone = body.timezone.strip() or None

    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/password/change", status_code=204)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change password after verifying the current one."""
    from datetime import datetime
    from app.utils.audit import add_audit
    from app.utils.security import verify_password, hash_password

    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    current_user.password_hash = hash_password(body.new_password)
    current_user.updated_at = datetime.utcnow()
    add_audit(db, user_id=current_user.id, action="password_changed", request=request, metadata={})
    await db.commit()


# ── Email verification ────────────────────────────────────────────────────────

@router.post("/verify-email/request", status_code=202)
@limiter.limit("5/hour")
async def request_email_verification(
    request: Request,
    current_user=Depends(get_current_user),
) -> dict:
    """Send (or re-send) the verification email for the logged-in user."""
    await account_service.send_verification(current_user)
    return {"ok": True}


@router.post("/verify-email", status_code=200)
@limiter.limit("20/hour")
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm an email address from the token in the verification link."""
    await account_service.confirm_verification(body.token, db)
    return {"ok": True}


# ── Password reset (forgot password) ─────────────────────────────────────────

@router.post("/password/forgot", status_code=202)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a reset link if the account exists. Always returns 202 (no enumeration)."""
    await account_service.request_password_reset(
        body.email, db, ip_address=request.client.host if request.client else None,
    )
    return {"ok": True}


@router.post("/password/reset", status_code=204)
@limiter.limit("10/hour")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Set a new password using a valid, unused reset token."""
    await account_service.reset_password(
        body.token, body.new_password, db,
        ip_address=request.client.host if request.client else None,
    )


# ── Account deletion ──────────────────────────────────────────────────────────

@router.delete("/me", status_code=204)
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    response: Response,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete the account, its data, and stored files."""
    await account_service.delete_account(
        current_user, body.password, db,
        ip_address=request.client.host if request.client else None,
    )
    clear_auth_cookies(response)

# LogRaven — Auth Routes
#
# HTTP handlers; business logic in services/auth_service.py.
# httpOnly cookies for browsers; JSON tokens optional (INCLUDE_TOKENS_IN_AUTH_JSON).

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
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
    ResetVerifyResponse,
    UpdateProfileRequest,
    UserCreate,
    UserLogin,
    UserResponse,
    VerifyEmailRequest,
    validate_strict_single_email,
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
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token, request=request)
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
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token, request=request)
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
    set_auth_cookies(response, result["access_token"], result["refresh_token"], request=request)
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
    clear_auth_cookies(response, request=request)
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
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change password after verifying the current one."""
    from datetime import datetime
    from app.services import auth_service
    from app.utils.audit import add_audit
    from app.utils.password_policy import validate_password_complexity
    from app.utils.security import verify_password, hash_password

    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    validate_password_complexity(body.new_password, current_user.email)

    current_user.password_hash = hash_password(body.new_password)
    current_user.updated_at = datetime.utcnow()
    await auth_service.revoke_all_user_tokens(current_user.id)
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


# ── Cryptographic Public Key Distribution ─────────────────────────────────────

@router.get("/crypto/public-key")
async def get_crypto_public_key(response: Response) -> dict:
    """Returns the active RSA-OAEP public key for client-side hybrid payload encryption."""
    from app.utils.crypto_envelope import get_crypto_envelope_manager

    manager = get_crypto_envelope_manager()
    response.headers["Cache-Control"] = "public, max-age=3600"
    return manager.get_public_key_info()


# ── Password reset (forgot password) ─────────────────────────────────────────

@router.get("/password/reset/verify", response_model=ResetVerifyResponse)
@limiter.limit("30/hour")
async def verify_password_reset_token(
    request: Request,
    response: Response,
    token: str = Query(..., description="Reset password token to verify"),
    db: AsyncSession = Depends(get_db),
) -> ResetVerifyResponse:
    """
    Idempotent pre-flight token check before displaying reset password form.
    Validates token signature, expiration, and single-use status without consuming it.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    result = await account_service.verify_reset_token(token, db)
    return ResetVerifyResponse(
        valid=result["valid"],
        email_masked=result.get("email_masked"),
    )


@router.post("/password/forgot", status_code=202)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    response: Response,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Send a reset link if the account exists.
    Always returns HTTP 202 and identical neutral message (zero-knowledge anti-enumeration).
    Supports either cleartext email or RSA-OAEP/AES-GCM encrypted envelope.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    target_email: str | None = None

    if body.envelope is not None:
        from app.utils.crypto_envelope import get_crypto_envelope_manager

        manager = get_crypto_envelope_manager()
        decrypted = manager.decrypt_envelope(body.envelope)
        raw_email = decrypted.get("email")
        if not raw_email or not isinstance(raw_email, str):
            raise HTTPException(status_code=400, detail="Decrypted payload missing 'email' string")
        target_email = validate_strict_single_email(raw_email)
    elif body.email is not None:
        target_email = body.email
    else:
        raise HTTPException(status_code=400, detail="Either 'email' or 'envelope' must be provided")

    await account_service.request_password_reset(
        target_email, db, ip_address=request.client.host if request.client else None,
    )
    return {
        "ok": True,
        "message": "If an account exists for the provided email, a password reset link has been dispatched.",
    }


@router.post("/password/reset", status_code=204)
@limiter.limit("10/hour")
async def reset_password(
    request: Request,
    response: Response,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Set a new password using a valid, unused reset token.
    Supports either cleartext or RSA-OAEP/AES-GCM encrypted envelope.
    Revokes all active sessions upon success.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    target_token: str | None = None
    target_password: str | None = None

    if body.envelope is not None:
        from app.utils.crypto_envelope import get_crypto_envelope_manager

        manager = get_crypto_envelope_manager()
        decrypted = manager.decrypt_envelope(body.envelope)
        target_token = decrypted.get("token")
        target_password = decrypted.get("new_password")
        if not target_token or not target_password:
            raise HTTPException(
                status_code=400,
                detail="Decrypted payload must contain both 'token' and 'new_password'",
            )
    elif body.token and body.new_password:
        target_token = body.token
        target_password = body.new_password
    else:
        raise HTTPException(status_code=400, detail="Token and new password required")

    await account_service.reset_password(
        target_token,
        target_password,
        db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    clear_auth_cookies(response, request=request)


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
    clear_auth_cookies(response, request=request)

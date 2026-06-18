# LogRaven — Security Utilities
#
# JWT (PyJWT), bcrypt passwords, short-lived signed download tokens for local files.

from datetime import datetime, timedelta, timezone
import uuid

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Precomputed bcrypt hash used to equalize password-verification timing on the
# "user not found" login path, mitigating username enumeration via timing.
DUMMY_PASSWORD_HASH = pwd_context.hash("lograven-dummy-password")

FILE_DOWNLOAD_TOKEN_EXPIRE_MINUTES = 15
FILE_DOWNLOAD_TOKEN_AUDIENCE = "lograven-download"

AUDIT_SHARE_TOKEN_AUDIENCE = "lograven-audit-share"


def hash_password(plain: str) -> str:
    truncated = plain.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(truncated)


def verify_password(plain: str, hashed: str) -> bool:
    truncated = plain.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.verify(truncated, hashed)


def create_access_token(user_id: str, tier: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "tier": tier,
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": jti,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """
    Decode and validate an access or refresh JWT.
    Raises HTTP 401 on any validation failure.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_file_download_token(storage_key: str, owner_user_id: str) -> str:
    """Short-lived JWT: one download of *storage_key*, only for *owner_user_id* (with session cookie)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=FILE_DOWNLOAD_TOKEN_EXPIRE_MINUTES)
    payload = {
        "typ": "file_dl",
        "key": storage_key,
        "dl_uid": owner_user_id,
        "iss": settings.JWT_ISSUER,
        "aud": FILE_DOWNLOAD_TOKEN_AUDIENCE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_file_download_token(token: str) -> tuple[str, str]:
    """Return (storage_key, owner_user_id)."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=FILE_DOWNLOAD_TOKEN_AUDIENCE,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Download link expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid download link")

    if payload.get("typ") != "file_dl":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid download link")
    key = payload.get("key")
    owner = payload.get("dl_uid")
    if not key or not isinstance(key, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid download link")
    if not owner or not isinstance(owner, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid download link")
    return key, owner


def create_audit_share_token(audit_id: str, expire_days: int = 7) -> str:
    """Read-only, expiring share token granting access to one audit's results (no auth)."""
    expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    payload = {
        "typ": "audit_share",
        "audit_id": audit_id,
        "iss": settings.JWT_ISSUER,
        "aud": AUDIT_SHARE_TOKEN_AUDIENCE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_audit_share_token(token: str) -> str:
    """Return the audit_id encoded in a share token (raises 401 if invalid/expired)."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=AUDIT_SHARE_TOKEN_AUDIENCE,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Share link expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid share link")

    if payload.get("typ") != "audit_share":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid share link")
    audit_id = payload.get("audit_id")
    if not audit_id or not isinstance(audit_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid share link")
    return audit_id

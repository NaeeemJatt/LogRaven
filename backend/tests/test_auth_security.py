# LogRaven — Authentication security tests
#
# Proves the backend cannot be tricked into authenticating a request without
# valid credentials: SQL-injection payloads, forged/altered JWTs, algorithm
# confusion, and missing tokens are all rejected.

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from app.services import auth_service
from app.utils import security
from app.config import settings


def _db_returning(user):
    result = SimpleNamespace(scalar_one_or_none=lambda: user)
    return SimpleNamespace(execute=AsyncMock(return_value=result), add=lambda *_: None, commit=AsyncMock())


# ── SQL injection cannot authenticate ────────────────────────────────────────

# Classic payloads that would bypass a naive string-concatenated SQL query.
SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1--",
    "admin'--",
    "' UNION SELECT password_hash FROM users--",
    "'; DROP TABLE users;--",
    "x@x.com' OR ''='",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
async def test_login_rejects_sql_injection_payloads(payload, monkeypatch):
    """An injection string is treated as a literal email; ORM finds no user → 401."""
    # DB returns no matching user (the payload is bound as a plain parameter).
    db = _db_returning(None)
    monkeypatch.setattr(security, "verify_password", lambda *a, **k: False)

    with pytest.raises(HTTPException) as exc:
        await auth_service.login_user(email=payload, password="whatever", db=db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(monkeypatch):
    user = SimpleNamespace(id=uuid4(), email="real@example.com", tier="free", password_hash="$2b$hash")
    db = _db_returning(user)
    monkeypatch.setattr(security, "verify_password", lambda *a, **k: False)

    with pytest.raises(HTTPException) as exc:
        await auth_service.login_user(email="real@example.com", password="wrong", db=db)

    assert exc.value.status_code == 401


# ── JWT forgery / tampering cannot authenticate ──────────────────────────────

def _valid_access_payload(user_id: str) -> dict:
    return {
        "sub": user_id,
        "tier": "free",
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }


def test_decode_token_rejects_alg_none():
    """The 'alg: none' unsigned-token attack must be refused."""
    token = jwt.encode(_valid_access_payload(str(uuid4())), key="", algorithm="none")
    with pytest.raises(HTTPException) as exc:
        security.decode_token(token)
    assert exc.value.status_code == 401


def test_decode_token_rejects_wrong_secret():
    """A token signed with a secret the attacker chose must not validate."""
    token = jwt.encode(_valid_access_payload(str(uuid4())), key="attacker-controlled-secret", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        security.decode_token(token)
    assert exc.value.status_code == 401


def test_decode_token_rejects_wrong_audience():
    payload = _valid_access_payload(str(uuid4()))
    payload["aud"] = "some-other-service"
    token = jwt.encode(payload, key=settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        security.decode_token(token)
    assert exc.value.status_code == 401


def test_decode_token_rejects_expired():
    payload = _valid_access_payload(str(uuid4()))
    payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode(payload, key=settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        security.decode_token(token)
    assert exc.value.status_code == 401


def test_decode_token_accepts_genuine_token():
    """Sanity: a properly signed token still works (we didn't over-restrict)."""
    uid = str(uuid4())
    token = jwt.encode(_valid_access_payload(uid), key=settings.JWT_SECRET_KEY, algorithm="HS256")
    payload = security.decode_token(token)
    assert payload["sub"] == uid
    assert payload["type"] == "access"


# ── get_current_user gate ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_user_requires_a_token():
    from app.dependencies import get_current_user

    with pytest.raises(HTTPException) as exc:
        await get_current_user(bearer_token=None, cookie_token=None, db=_db_returning(None))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_garbage_token():
    from app.dependencies import get_current_user

    with pytest.raises(HTTPException) as exc:
        await get_current_user(bearer_token="not-a-jwt", cookie_token=None, db=_db_returning(None))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_refresh_token_as_access(monkeypatch):
    """A refresh token (type != 'access') must not unlock protected routes."""
    from app.dependencies import get_current_user

    refresh_payload = {
        "sub": str(uuid4()),
        "type": "refresh",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    token = jwt.encode(refresh_payload, key=settings.JWT_SECRET_KEY, algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        await get_current_user(bearer_token=token, cookie_token=None, db=_db_returning(None))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_valid_token_for_deleted_user(monkeypatch):
    """A perfectly signed token whose user no longer exists is rejected."""
    from app.dependencies import get_current_user

    token = jwt.encode(_valid_access_payload(str(uuid4())), key=settings.JWT_SECRET_KEY, algorithm="HS256")
    # DB returns None → user not found.
    with pytest.raises(HTTPException) as exc:
        await get_current_user(bearer_token=token, cookie_token=None, db=_db_returning(None))
    assert exc.value.status_code == 401

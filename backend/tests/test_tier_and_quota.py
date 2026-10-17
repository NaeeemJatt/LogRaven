# LogRaven — Tests: admin tier gate, email-verification login gate, daily quota

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.config import settings
from app.services import auth_service
from app.utils import security


def _db_returning(user):
    result = SimpleNamespace(scalar_one_or_none=lambda: user)
    return SimpleNamespace(execute=AsyncMock(return_value=result), add=lambda *_: None, commit=AsyncMock())


# ── Admin gate (ADMIN_EMAILS) ─────────────────────────────────────────────────

class TestAdminGate:

    def _gate(self, admin_emails: str, caller_email: str):
        from app.api.admin import routes as admin_routes
        mock_settings = MagicMock()
        mock_settings.ADMIN_EMAILS = admin_emails
        caller = SimpleNamespace(id=uuid4(), email=caller_email)
        with patch("app.api.admin.routes.settings", mock_settings):
            return admin_routes.require_admin(caller)

    def test_listed_admin_passes(self):
        user = self._gate("ops@lograven.io, admin@lograven.io", "admin@lograven.io")
        assert user.email == "admin@lograven.io"

    def test_admin_match_is_case_insensitive(self):
        user = self._gate("Admin@LogRaven.io", "admin@lograven.io")
        assert user.email == "admin@lograven.io"

    def test_non_admin_gets_404(self):
        with pytest.raises(HTTPException) as exc:
            self._gate("admin@lograven.io", "user@example.com")
        assert exc.value.status_code == 404

    def test_empty_admin_list_disables_endpoint_for_everyone(self):
        with pytest.raises(HTTPException) as exc:
            self._gate("", "admin@lograven.io")
        assert exc.value.status_code == 404


# ── Email-verification login gate (opt-in) ────────────────────────────────────

@pytest.mark.asyncio
async def test_unverified_login_blocked_when_gate_enabled(monkeypatch):
    user = SimpleNamespace(
        id=uuid4(), email="u@example.com", tier="free",
        password_hash="$2b$hash", email_verified=False,
    )
    db = _db_returning(user)
    monkeypatch.setattr(security, "verify_password", lambda *a, **k: True)
    monkeypatch.setattr(settings, "REQUIRE_VERIFIED_EMAIL_FOR_LOGIN", True)

    with pytest.raises(HTTPException) as exc:
        await auth_service.login_user(email="u@example.com", password="correct", db=db)

    assert exc.value.status_code == 403
    assert "verify" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_unverified_login_allowed_when_gate_disabled(monkeypatch):
    from datetime import datetime
    user = SimpleNamespace(
        id=uuid4(), email="u@example.com", tier="free",
        password_hash="$2b$hash", email_verified=False,
        name=None, timezone=None, created_at=datetime.utcnow(),
    )
    db = _db_returning(user)
    monkeypatch.setattr(security, "verify_password", lambda *a, **k: True)
    monkeypatch.setattr(settings, "REQUIRE_VERIFIED_EMAIL_FOR_LOGIN", False)
    monkeypatch.setattr(
        "app.utils.refresh_tokens.store_refresh_token", AsyncMock(return_value=None)
    )

    tokens = await auth_service.login_user(email="u@example.com", password="correct", db=db)
    assert tokens.access_token


# ── Per-tier daily analysis quota ─────────────────────────────────────────────

def _redis_mock(incr_value: int):
    client = AsyncMock()
    client.incr = AsyncMock(return_value=incr_value)
    client.decr = AsyncMock(return_value=incr_value - 1)
    client.expire = AsyncMock(return_value=True)
    client.aclose = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_quota_allows_under_limit(monkeypatch):
    from app.utils import rate_limiter
    monkeypatch.setattr(settings, "DAILY_ANALYSES_FREE", 5)
    with patch("app.utils.rate_limiter.aioredis.from_url", return_value=_redis_mock(3)):
        allowed, remaining = await rate_limiter.check_and_count_analysis(str(uuid4()), "free")
    assert allowed is True
    assert remaining == 2


@pytest.mark.asyncio
async def test_quota_blocks_over_limit_and_rolls_back(monkeypatch):
    from app.utils import rate_limiter
    monkeypatch.setattr(settings, "DAILY_ANALYSES_FREE", 5)
    client = _redis_mock(6)  # over the limit of 5
    with patch("app.utils.rate_limiter.aioredis.from_url", return_value=client):
        allowed, remaining = await rate_limiter.check_and_count_analysis(str(uuid4()), "free")
    assert allowed is False
    assert remaining == 0
    client.decr.assert_awaited_once()  # rejected attempt must not consume quota


@pytest.mark.asyncio
async def test_quota_zero_means_unlimited(monkeypatch):
    from app.utils import rate_limiter
    monkeypatch.setattr(settings, "DAILY_ANALYSES_TEAM", 0)
    allowed, remaining = await rate_limiter.check_and_count_analysis(str(uuid4()), "team")
    assert allowed is True
    assert remaining == -1


@pytest.mark.asyncio
async def test_quota_fails_open_when_redis_down(monkeypatch):
    from app.utils import rate_limiter
    monkeypatch.setattr(settings, "DAILY_ANALYSES_FREE", 5)
    with patch(
        "app.utils.rate_limiter.aioredis.from_url",
        side_effect=ConnectionError("redis down"),
    ):
        allowed, remaining = await rate_limiter.check_and_count_analysis(str(uuid4()), "free")
    assert allowed is True  # availability wins over metering
    assert remaining == -1


@pytest.mark.asyncio
async def test_quota_refund_is_atomic_and_never_decrements_below_zero(monkeypatch):
    from app.utils import rate_limiter

    monkeypatch.setattr(settings, "DAILY_ANALYSES_FREE", 5)
    client = _redis_mock(1)
    client.eval = AsyncMock(return_value=1)

    with patch("app.utils.rate_limiter.aioredis.from_url", return_value=client):
        refunded = await rate_limiter.refund_analysis_quota("user-1", "free")

    assert refunded is True
    script, key_count, key = client.eval.await_args.args
    assert "current <= 0" in script
    assert "DECR" in script
    assert key_count == 1
    assert key.startswith("lograven:daily-analyses:user-1:")
    client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_quota_refund_at_zero_is_a_safe_noop(monkeypatch):
    from app.utils import rate_limiter

    monkeypatch.setattr(settings, "DAILY_ANALYSES_FREE", 5)
    client = _redis_mock(0)
    client.eval = AsyncMock(return_value=0)

    with patch("app.utils.rate_limiter.aioredis.from_url", return_value=client):
        refunded = await rate_limiter.refund_analysis_quota("user-1", "free")

    assert refunded is False

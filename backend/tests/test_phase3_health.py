# Tests — Phase 3: Health Check
# Tests the pure _check_ai() function and module importability.
# _check_db and _check_redis require live services — tested with mocks.

import sys, os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _request(host: str = "127.0.0.1"):
    return SimpleNamespace(client=SimpleNamespace(host=host))


# ---------------------------------------------------------------------------
# Phase 3a: _check_ai (pure function — no network)
# ---------------------------------------------------------------------------

class TestCheckAi:
    """Only the wired provider (GEMINI_API_KEY) counts toward "AI enabled"."""

    def _run(self, gemini=""):
        """Helper: call _check_ai with patched provider key."""
        from app.api.health import routes as health_module
        mock_settings = MagicMock()
        mock_settings.GEMINI_API_KEY = gemini
        # cloud_ai_enabled binds settings at consent-module import — patch there.
        with patch("app.ai.cloud.consent.settings", mock_settings):
            return health_module._check_ai()

    def test_provider_key_returns_ok(self):
        result = self._run(gemini="AIza_test_key")
        assert result == "ok"

    def test_no_key_returns_no_key(self):
        result = self._run()
        assert result == "no_key"

    def test_empty_key_is_falsy(self):
        result = self._run(gemini="")
        assert result == "no_key"


# ---------------------------------------------------------------------------
# Phase 3b: _check_db — mock AsyncSessionLocal so no real DB needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_db_ok():
    from app.api.health import routes as health_module

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=None)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__  = AsyncMock(return_value=False)

    with patch("app.dependencies.AsyncSessionLocal", return_value=mock_cm):
        result = await health_module._check_db()
    assert result == "ok"


@pytest.mark.asyncio
async def test_check_db_error_on_exception():
    from app.api.health import routes as health_module

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
    mock_cm.__aexit__  = AsyncMock(return_value=False)

    with patch("app.dependencies.AsyncSessionLocal", return_value=mock_cm):
        result = await health_module._check_db()
    assert result == "error"


# ---------------------------------------------------------------------------
# Phase 3c: _check_redis — mock redis.asyncio so no real Redis needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_redis_ok():
    from app.api.health import routes as health_module

    mock_client = AsyncMock()
    mock_client.ping  = AsyncMock(return_value=True)
    mock_client.aclose = AsyncMock(return_value=None)

    mock_settings = MagicMock()
    mock_settings.REDIS_URL = "redis://localhost:6379"

    with patch("app.config.settings", mock_settings), \
         patch("redis.asyncio.from_url", return_value=mock_client):
        result = await health_module._check_redis()
    assert result == "ok"


@pytest.mark.asyncio
async def test_check_redis_error_on_timeout():
    from app.api.health import routes as health_module

    mock_client = AsyncMock()
    mock_client.ping  = AsyncMock(side_effect=Exception("Connection timeout"))
    mock_client.aclose = AsyncMock(return_value=None)

    mock_settings = MagicMock()
    mock_settings.REDIS_URL = "redis://localhost:6379"

    with patch("app.config.settings", mock_settings), \
         patch("redis.asyncio.from_url", return_value=mock_client):
        result = await health_module._check_redis()
    assert result == "error"


# ---------------------------------------------------------------------------
# Phase 3d: health_check endpoint — overall status logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check_status_ok_when_all_pass():
    from app.api.health import routes as health_module
    with patch.object(health_module, "_check_db",    AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_redis", AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_ai",    MagicMock(return_value="ok")), \
         patch.object(health_module, "settings", MagicMock(DEBUG=True)):
        result = await health_module.health_check(_request())
    assert result["status"] == "ok"
    assert result["db"]    == "ok"
    assert result["redis"] == "ok"
    assert result["ai"]    == "ok"


@pytest.mark.asyncio
async def test_health_check_status_degraded_when_db_down():
    from app.api.health import routes as health_module
    with patch.object(health_module, "_check_db",    AsyncMock(return_value="error")), \
         patch.object(health_module, "_check_redis", AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_ai",    MagicMock(return_value="ok")), \
         patch.object(health_module, "settings", MagicMock(DEBUG=True)):
        result = await health_module.health_check(_request())
    assert result["status"] == "degraded"
    assert result["db"]     == "error"


@pytest.mark.asyncio
async def test_health_check_status_degraded_when_redis_down():
    from app.api.health import routes as health_module
    with patch.object(health_module, "_check_db",    AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_redis", AsyncMock(return_value="error")), \
         patch.object(health_module, "_check_ai",    MagicMock(return_value="ok")), \
         patch.object(health_module, "settings", MagicMock(DEBUG=True)):
        result = await health_module.health_check(_request())
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_ok_even_with_no_ai_key():
    """Missing AI key should NOT degrade overall status."""
    from app.api.health import routes as health_module
    with patch.object(health_module, "_check_db",    AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_redis", AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_ai",    MagicMock(return_value="no_key")), \
         patch.object(health_module, "settings", MagicMock(DEBUG=True)):
        result = await health_module.health_check(_request())
    assert result["status"] == "ok"
    assert result["ai"]     == "no_key"


@pytest.mark.asyncio
async def test_health_check_hides_dependency_detail_outside_debug():
    from app.api.health import routes as health_module
    with patch.object(health_module, "_check_db",    AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_redis", AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_ai",    MagicMock(return_value="ok")), \
         patch.object(health_module, "settings", MagicMock(DEBUG=False)):
        result = await health_module.health_check(_request())
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_hides_dependency_detail_for_remote_clients_even_in_debug():
    from app.api.health import routes as health_module
    with patch.object(health_module, "_check_db",    AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_redis", AsyncMock(return_value="ok")), \
         patch.object(health_module, "_check_ai",    MagicMock(return_value="ok")), \
         patch.object(health_module, "settings", MagicMock(DEBUG=True)):
        result = await health_module.health_check(_request("203.0.113.10"))
    assert result == {"status": "ok"}


# ---------------------------------------------------------------------------
# Phase 3e: health route import sanity
# ---------------------------------------------------------------------------

def test_health_route_importable():
    from app.api.health.routes import router, health_check
    assert router is not None
    assert callable(health_check)

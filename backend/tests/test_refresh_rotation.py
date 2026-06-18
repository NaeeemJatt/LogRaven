from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import AsyncMock

import pytest

from app.services import auth_service


def _db_with_user(user):
    result = SimpleNamespace(scalar_one_or_none=lambda: user)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    return db


@pytest.mark.asyncio
async def test_refresh_token_returns_cached_rotation_without_consuming(monkeypatch):
    user_id = str(uuid4())
    cached = {
        "access_token": "cached-access",
        "refresh_token": "cached-refresh",
        "token_type": "bearer",
    }

    monkeypatch.setattr(auth_service.security, "decode_token", lambda token: {
        "type": "refresh",
        "sub": user_id,
        "jti": "old-jti",
    })
    monkeypatch.setattr(auth_service.refresh_tokens, "get_refresh_result", AsyncMock(return_value=cached))
    monkeypatch.setattr(auth_service.refresh_tokens, "consume_refresh_token", AsyncMock(side_effect=AssertionError("should not consume")))

    result = await auth_service.refresh_token("token", _db_with_user(SimpleNamespace(id=user_id, tier="free")))

    assert result == cached


@pytest.mark.asyncio
async def test_refresh_token_rotates_once_and_stores_replay_result(monkeypatch):
    user_id = str(uuid4())
    created_at = datetime(2026, 4, 2, 12, 0, 0)
    user = SimpleNamespace(id=UUID(user_id), email="user@example.com", tier="pro", created_at=created_at)

    monkeypatch.setattr(auth_service.security, "decode_token", lambda token: {
        "type": "refresh",
        "sub": user_id,
        "jti": "old-jti",
    })
    monkeypatch.setattr(auth_service.refresh_tokens, "get_refresh_result", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service.refresh_tokens, "acquire_refresh_lock", AsyncMock(return_value=True))
    monkeypatch.setattr(auth_service.refresh_tokens, "consume_refresh_token", AsyncMock(return_value=True))
    monkeypatch.setattr(auth_service.refresh_tokens, "release_refresh_lock", AsyncMock())
    monkeypatch.setattr(auth_service.security, "create_refresh_token", lambda _: ("new-refresh", "new-jti"))
    monkeypatch.setattr(auth_service.security, "create_access_token", lambda *_: "new-access")
    store_rotation = AsyncMock()
    monkeypatch.setattr(auth_service.refresh_tokens, "store_refresh_rotation_result", store_rotation)

    result = await auth_service.refresh_token("token", _db_with_user(user))

    assert result == {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": "user@example.com",
            "tier": "pro",
            "name": None,
            "timezone": None,
            "created_at": "2026-04-02T12:00:00",
        },
    }
    store_rotation.assert_awaited_once_with("old-jti", user_id, "new-jti", "new-access", "new-refresh")
    auth_service.refresh_tokens.release_refresh_lock.assert_awaited_once_with("old-jti")


@pytest.mark.asyncio
async def test_refresh_token_reuses_recent_rotation_after_old_jti_consumed(monkeypatch):
    user_id = str(uuid4())
    user = SimpleNamespace(id=uuid4(), tier="free")
    cached = {
        "access_token": "cached-access",
        "refresh_token": "cached-refresh",
        "token_type": "bearer",
    }

    monkeypatch.setattr(auth_service.security, "decode_token", lambda token: {
        "type": "refresh",
        "sub": user_id,
        "jti": "old-jti",
    })
    monkeypatch.setattr(
        auth_service.refresh_tokens,
        "get_refresh_result",
        AsyncMock(side_effect=[None, None, cached]),
    )
    monkeypatch.setattr(auth_service.refresh_tokens, "acquire_refresh_lock", AsyncMock(return_value=True))
    monkeypatch.setattr(auth_service.refresh_tokens, "consume_refresh_token", AsyncMock(return_value=False))
    monkeypatch.setattr(auth_service.refresh_tokens, "release_refresh_lock", AsyncMock())

    result = await auth_service.refresh_token("token", _db_with_user(user))

    assert result == cached
    auth_service.refresh_tokens.release_refresh_lock.assert_awaited_once_with("old-jti")


@pytest.mark.asyncio
async def test_refresh_token_normalizes_user_id_for_replay_cache(monkeypatch):
    user_uuid = uuid4()
    non_canonical_user_id = "{" + str(user_uuid).upper() + "}"
    user = SimpleNamespace(
        id=user_uuid,
        email="user@example.com",
        tier="free",
        created_at=datetime(2026, 4, 2, 12, 0, 0),
    )

    monkeypatch.setattr(auth_service.security, "decode_token", lambda token: {
        "type": "refresh",
        "sub": non_canonical_user_id,
        "jti": "old-jti",
    })
    get_refresh_result = AsyncMock(return_value=None)
    monkeypatch.setattr(auth_service.refresh_tokens, "get_refresh_result", get_refresh_result)
    monkeypatch.setattr(auth_service.refresh_tokens, "acquire_refresh_lock", AsyncMock(return_value=True))
    monkeypatch.setattr(auth_service.refresh_tokens, "consume_refresh_token", AsyncMock(return_value=True))
    monkeypatch.setattr(auth_service.refresh_tokens, "release_refresh_lock", AsyncMock())
    monkeypatch.setattr(auth_service.security, "create_refresh_token", lambda _: ("new-refresh", "new-jti"))
    monkeypatch.setattr(auth_service.security, "create_access_token", lambda *_: "new-access")
    store_rotation = AsyncMock()
    monkeypatch.setattr(auth_service.refresh_tokens, "store_refresh_rotation_result", store_rotation)

    await auth_service.refresh_token("token", _db_with_user(user))

    canonical_user_id = str(user_uuid)
    get_refresh_result.assert_awaited_with("old-jti", canonical_user_id)
    auth_service.refresh_tokens.consume_refresh_token.assert_awaited_once_with("old-jti", canonical_user_id)
    store_rotation.assert_awaited_once_with("old-jti", canonical_user_id, "new-jti", "new-access", "new-refresh")

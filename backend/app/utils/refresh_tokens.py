from __future__ import annotations

import json
from datetime import timedelta

import redis.asyncio as aioredis

from app.config import settings

_PREFIX = "lograven:refresh:"
_RESULT_PREFIX = "lograven:refresh-result:"
_LOCK_PREFIX = "lograven:refresh-lock:"
_REFRESH_RESULT_TTL_SECONDS = 60
_REFRESH_LOCK_TTL_SECONDS = 10

_CONSUME_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if not value then
    return 0
end
if value ~= ARGV[1] then
    return -1
end
redis.call('DEL', KEYS[1])
return 1
"""


def _key(jti: str) -> str:
    return f"{_PREFIX}{jti}"


def _result_key(jti: str) -> str:
    return f"{_RESULT_PREFIX}{jti}"


def _lock_key(jti: str) -> str:
    return f"{_LOCK_PREFIX}{jti}"


def _ttl_seconds() -> int:
    return max(1, int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()))


def _client():
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def store_refresh_token(jti: str, user_id: str) -> None:
    client = _client()
    try:
        await client.set(_key(jti), user_id, ex=_ttl_seconds())
    finally:
        await client.aclose()


async def consume_refresh_token(jti: str, user_id: str) -> bool:
    client = _client()
    try:
        result = await client.eval(_CONSUME_SCRIPT, 1, _key(jti), user_id)
        return result == 1
    finally:
        await client.aclose()


async def revoke_refresh_token(jti: str) -> None:
    client = _client()
    try:
        await client.delete(_key(jti))
    finally:
        await client.aclose()


async def acquire_refresh_lock(jti: str) -> bool:
    client = _client()
    try:
        return bool(await client.set(_lock_key(jti), "1", ex=_REFRESH_LOCK_TTL_SECONDS, nx=True))
    finally:
        await client.aclose()


async def release_refresh_lock(jti: str) -> None:
    client = _client()
    try:
        await client.delete(_lock_key(jti))
    finally:
        await client.aclose()


async def get_refresh_result(jti: str, user_id: str) -> dict | None:
    client = _client()
    try:
        raw = await client.get(_result_key(jti))
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if payload.get("user_id") != user_id:
            return None
        return {
            "access_token": payload["access_token"],
            "refresh_token": payload["refresh_token"],
            "token_type": "bearer",
        }
    finally:
        await client.aclose()


async def store_refresh_rotation_result(
    old_jti: str,
    user_id: str,
    new_jti: str,
    access_token: str,
    refresh_token: str,
) -> None:
    client = _client()
    try:
        pipe = client.pipeline()
        pipe.set(_key(new_jti), user_id, ex=_ttl_seconds())
        pipe.set(
            _result_key(old_jti),
            json.dumps({
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
            }),
            ex=_REFRESH_RESULT_TTL_SECONDS,
        )
        await pipe.execute()
    finally:
        await client.aclose()

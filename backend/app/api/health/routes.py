# LogRaven — Health Check Route
#
# GET /health — no auth required
#
# Checks:
#   db    — async SELECT 1 against PostgreSQL
#   redis — PING against Redis using redis.asyncio
#   ai    — whether an AI API key is configured (no outbound call)
#
# Response shape:
#   {"status": "ok"|"degraded", "db": "ok"|"error", "redis": "ok"|"error", "ai": "ok"|"no_key"}
#
# "degraded" is returned when db or redis are unreachable.
# AI key absence downgrades ai to "no_key" but does NOT affect overall status,
# since analysis can be skipped and the app still functions.

from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health_check():
    db_status    = await _check_db()
    redis_status = await _check_redis()
    ai_status    = _check_ai()

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return {
        "status": overall,
        "db":     db_status,
        "redis":  redis_status,
        "ai":     ai_status,
    }


async def _check_db() -> str:
    """Try a lightweight SELECT 1 through the shared async engine."""
    try:
        from app.dependencies import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def _check_redis() -> str:
    """Attempt a PING to Redis with a 2-second socket timeout."""
    try:
        import redis.asyncio as aioredis
        from app.config import settings
        client = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception:
        return "error"


def _check_ai() -> str:
    """
    Return 'ok' if at least one AI API key is configured, 'no_key' otherwise.
    Does not make any outbound network call.
    """
    from app.config import settings
    if any([settings.GEMINI_API_KEY, settings.ANTHROPIC_API_KEY, settings.OPENAI_API_KEY]):
        return "ok"
    return "no_key"

# LogRaven — Per-tier daily analysis quota
#
# PURPOSE:
#   Caps how many investigations a user can send to analysis per UTC day.
#   Complements SlowAPI (per-IP request rates) with a per-account business
#   quota driven by tier.
#
# LIMITS (env-overridable via DAILY_ANALYSES_FREE / _PRO / _TEAM; 0 = unlimited):
#   free: 5 analyses/day   pro: 50/day   team: 200/day
#
# STORAGE:
#   Redis INCR + EXPIRE on a per-user, per-day key — atomic and shared across
#   API replicas. If Redis is unreachable the quota FAILS OPEN (analysis is
#   allowed): availability of the core product wins over strict metering.

from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "lograven:daily-analyses:"
_DAY_TTL_SECONDS = 60 * 60 * 24 + 60 * 60  # 25h: outlives the UTC day it counts
_REFUND_SCRIPT = """
local current = tonumber(redis.call("GET", KEYS[1]) or "0")
if current <= 0 then
    return 0
end
redis.call("DECR", KEYS[1])
return 1
"""


def tier_daily_limits() -> dict[str, int]:
    return {
        "free": settings.DAILY_ANALYSES_FREE,
        "pro":  settings.DAILY_ANALYSES_PRO,
        "team": settings.DAILY_ANALYSES_TEAM,
    }


def _key(user_id: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{_KEY_PREFIX}{user_id}:{day}"


async def check_and_count_analysis(user_id: str, tier: str) -> tuple[bool, int]:
    """
    Atomically count one analysis attempt against today's quota.

    Returns (allowed, remaining_after_this). When the quota is exceeded the
    counter is rolled back so retries tomorrow aren't penalised by today's
    rejected attempts.
    """
    limit = tier_daily_limits().get(tier, settings.DAILY_ANALYSES_FREE)
    if limit <= 0:
        return True, -1  # unlimited

    key = _key(user_id)
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            used = await client.incr(key)
            if used == 1:
                await client.expire(key, _DAY_TTL_SECONDS)
            if used > limit:
                await client.decr(key)
                return False, 0
            return True, limit - used
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001 — fail open on Redis outage
        logger.warning("Daily-analysis quota check skipped (Redis unavailable): %s", exc)
        return True, -1


async def refund_analysis_quota(user_id: str, tier: str) -> bool:
    """Best-effort atomic refund; never allow the daily counter below zero."""
    limit = tier_daily_limits().get(tier, settings.DAILY_ANALYSES_FREE)
    if limit <= 0:
        return False

    client = None
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return bool(await client.eval(_REFUND_SCRIPT, 1, _key(user_id)))
    except Exception as exc:  # noqa: BLE001 — dispatch compensation must still complete
        logger.warning("Daily-analysis quota refund skipped (Redis unavailable): %s", exc)
        return False
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception as exc:  # noqa: BLE001 — refund remains best-effort
                logger.warning("Daily-analysis quota refund cleanup failed: %s", exc)

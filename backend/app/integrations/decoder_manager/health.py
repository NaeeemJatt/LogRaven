# LogRaven — decoder manager reachability with short TTL cache.

from __future__ import annotations

import time

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_cache_until: float = 0.0
_cache_ok: bool = False

_HEALTH_TTL_SEC = 45.0


def _decoder_configured() -> bool:
    return bool(
        (settings.DECODER_MANAGER_API_URL or "").strip()
        and (settings.DECODER_MANAGER_USER or "").strip()
        and (settings.DECODER_MANAGER_PASSWORD or "").strip()
    )


async def decoder_manager_is_healthy_cached() -> bool:
    """
    Return True if we can authenticate to the decoder manager API.
    Cached ~45s to avoid hammering a down service from many lines/files.
    """
    global _cache_until, _cache_ok
    now = time.monotonic()
    if now < _cache_until:
        return _cache_ok

    if not _decoder_configured():
        _cache_ok = False
        _cache_until = now + _HEALTH_TTL_SEC
        return False

    try:
        from app.integrations.decoder_manager.client import DecoderManagerClient

        client = DecoderManagerClient()
        token = await client.authenticate()
        _cache_ok = bool(token)
    except Exception as e:
        logger.warning("Decoder manager health check failed: %s", e)
        _cache_ok = False

    _cache_until = now + _HEALTH_TTL_SEC
    return _cache_ok


def invalidate_decoder_health_cache() -> None:
    global _cache_until
    _cache_until = 0.0

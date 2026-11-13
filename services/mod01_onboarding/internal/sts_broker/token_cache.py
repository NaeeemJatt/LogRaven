"""Redis & In-Memory Ephemeral Token Cache with 180s Expiration Margin (FR-MOD1-03)."""

import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # pragma: no cover


class TokenCache:
    """Manages short-lived cloud credentials with TTL = max(expiration - 180s, 60s)."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._redis: Optional[Union[Any, bool]] = None
        self._memory_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def _get_redis(self):
        if self._redis is None:
            if not self.redis_url or not aioredis:
                self._redis = False
            else:
                try:
                    client = aioredis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        socket_connect_timeout=0.2,
                        socket_timeout=0.2,
                    )
                    await asyncio.wait_for(client.ping(), timeout=0.3)
                    self._redis = client
                except Exception:
                    # Mark as permanently disabled for this instance so we don't block
                    self._redis = False

        return self._redis if self._redis is not False else None

    def _cache_key(self, tenant_id: str, account_id: str, provider: str = "aws") -> str:
        return f"lr:token:{tenant_id}:{provider}:{account_id}"

    async def get_credentials(
        self,
        tenant_id: str,
        account_id: str,
        provider: str = "aws",
    ) -> Optional[Dict[str, Any]]:
        """Retrieve active credentials if valid and not within 180s expiration margin."""
        key = self._cache_key(tenant_id, account_id, provider)
        now = time.time()

        r = await self._get_redis()
        if r:
            try:
                raw = await r.get(key)
                if raw:
                    data = json.loads(raw)
                    exp = data.get("expiration_timestamp", 0)
                    if exp - now > 180:
                        return data
                    # If within 180s window, treat as expired
                    await r.delete(key)
            except Exception:
                pass

        # Fallback to in-memory cache
        if key in self._memory_cache:
            data, exp = self._memory_cache[key]
            if exp - now > 180:
                return data
            else:
                del self._memory_cache[key]

        return None

    async def store_credentials(
        self,
        tenant_id: str,
        account_id: str,
        credentials: Dict[str, Any],
        expiration: datetime,
        provider: str = "aws",
    ) -> None:
        """Store credentials with TTL = max(expiration - 180s, 60s) + jitter."""
        key = self._cache_key(tenant_id, account_id, provider)
        now = time.time()
        exp_ts = expiration.timestamp() if isinstance(expiration, datetime) else float(expiration)
        credentials["expiration_timestamp"] = exp_ts

        # Calculate TTL with 180s safety margin + up to 15s random jitter
        jitter = random.uniform(0, 15)
        ttl = max(int(exp_ts - now - 180 + jitter), 60)

        # In-memory save
        self._memory_cache[key] = (credentials, exp_ts)

        # Redis save
        r = await self._get_redis()
        if r:
            try:
                await r.set(key, json.dumps(credentials), ex=ttl)
            except Exception:
                pass

    async def invalidate(self, tenant_id: str, account_id: str, provider: str = "aws") -> None:
        """Explicitly evict cached credentials."""
        key = self._cache_key(tenant_id, account_id, provider)
        self._memory_cache.pop(key, None)
        r = await self._get_redis()
        if r:
            try:
                await r.delete(key)
            except Exception:
                pass

    def get_lock(self, tenant_id: str, account_id: str) -> asyncio.Lock:
        """Atomic mutex preventing thundering herds on token refresh."""
        key = f"{tenant_id}:{account_id}"
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

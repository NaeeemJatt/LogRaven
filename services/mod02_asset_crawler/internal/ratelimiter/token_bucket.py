"""Token Bucket Rate Limiter with Jittered Exponential Backoff (TC-MOD2-004).

Throttles API requests per (account_id, region, service) to stay strictly within 60% of cloud provider rate limits and handles ThrottlingException / 429 errors gracefully.
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("lograven.crawler.ratelimiter")


class TokenBucketLimiter:
    """Async token bucket rate limiter supporting per-service buckets and full-jitter backoff."""

    def __init__(self, rate_per_second: float = 20.0, burst_capacity: int = 40):
        self.rate = rate_per_second
        self.capacity = burst_capacity
        self._buckets: Dict[str, Tuple[float, float]] = {} # key -> (tokens, last_update)
        self._lock = asyncio.Lock()

    def _bucket_key(self, account_id: str, region: str, service: str) -> str:
        return f"{account_id}:{region}:{service}"

    async def acquire(self, account_id: str, region: str, service: str, tokens: float = 1.0) -> None:
        """Acquires tokens from the bucket, sleeping if insufficient tokens are available."""
        key = self._bucket_key(account_id, region, service)

        while True:
            async with self._lock:
                now = time.time()
                curr_tokens, last_update = self._buckets.get(key, (self.capacity, now))

                # Refill tokens based on elapsed time
                elapsed = now - last_update
                curr_tokens = min(self.capacity, curr_tokens + elapsed * self.rate)

                if curr_tokens >= tokens:
                    self._buckets[key] = (curr_tokens - tokens, now)
                    return
                else:
                    needed = tokens - curr_tokens
                    wait_time = needed / self.rate
                    self._buckets[key] = (curr_tokens, now)

            # Sleep outside lock
            await asyncio.sleep(min(wait_time, 1.0))

    async def execute_with_backoff(
        self,
        func: Callable,
        *args,
        account_id: str = "default",
        region: str = "global",
        service: str = "default",
        max_attempts: int = 5,
        base_backoff: float = 0.1,
        max_backoff: float = 2.0,
        **kwargs,
    ) -> Any:
        """Executes a cloud API call with token-bucket rate limiting and jittered exponential backoff.
        
        Handles ThrottlingException, RequestLimitExceeded, RateLimitExceeded, and 429 responses.
        """
        attempt = 0
        backoff = base_backoff

        while attempt < max_attempts:
            attempt += 1
            await self.acquire(account_id, region, service)

            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as exc:
                err_str = str(exc)
                is_throttling = any(
                    x in err_str
                    for x in (
                        "Throttling",
                        "ThrottlingException",
                        "RequestLimitExceeded",
                        "RateLimitExceeded",
                        "TooManyRequests",
                        "429",
                    )
                )

                if is_throttling and attempt < max_attempts:
                    # Full Jitter backoff: sleep between 0 and backoff
                    sleep_time = random.uniform(0, min(max_backoff, backoff * (2 ** (attempt - 1))))
                    logger.warning(
                        "API Throttling on %s:%s:%s (attempt %d/%d). Backing off for %.3fs: %s",
                        account_id, region, service, attempt, max_attempts, sleep_time, err_str,
                    )
                    await asyncio.sleep(sleep_time)
                    continue

                raise


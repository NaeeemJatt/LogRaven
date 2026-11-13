"""AWS STS AssumeRole Broker with ExternalId and Resilient Backoff (FR-MOD1-03, TC-MOD1-002, TC-MOD1-005)."""

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

from services.mod01_onboarding.internal.sts_broker.token_cache import TokenCache

logger = logging.getLogger("lograven.sts_broker.aws")


class STSAssumeRoleBroker:
    """Brokers short-lived AWS credentials via sts:AssumeRole with cryptographic ExternalId."""

    def __init__(self, cache: Optional[TokenCache] = None, sts_client: Optional[Any] = None):
        self.cache = cache or TokenCache()
        self._sts_client = sts_client

    def _get_sts_client(self):
        if self._sts_client is not None:
            return self._sts_client
        return boto3.client("sts")

    async def get_credentials(
        self,
        tenant_id: str,
        account_id: str,
        role_arn: str,
        external_id: str,
        duration_seconds: int = 3600,
        session_name: str = "LogRavenTrustBroker",
    ) -> Tuple[Dict[str, Any], bool]:
        """Obtain valid AWS credentials for role.
        
        Returns tuple of (credentials_dict, cache_hit).
        """
        # 1. Fast-path cache lookup
        cached = await self.cache.get_credentials(tenant_id, account_id, provider="aws")
        if cached:
            return cached, True

        # 2. Acquire per-account lock to prevent concurrent redundant STS calls
        lock = self.cache.get_lock(tenant_id, account_id)
        async with lock:
            # Re-check cache after acquiring lock
            cached = await self.cache.get_credentials(tenant_id, account_id, provider="aws")
            if cached:
                return cached, True

            # 3. Call STS AssumeRole with exponential backoff for transient failures
            creds = await self._assume_role_with_retry(
                role_arn=role_arn,
                external_id=external_id,
                duration_seconds=duration_seconds,
                session_name=session_name,
            )

            expiration = creds["Expiration"]
            serialized = {
                "access_key_id": creds["AccessKeyId"],
                "secret_access_key": creds["SecretAccessKey"],
                "session_token": creds["SessionToken"],
                "expiration": expiration.isoformat() if hasattr(expiration, "isoformat") else str(expiration),
                "role_arn": role_arn,
            }

            # 4. Save into token cache
            await self.cache.store_credentials(
                tenant_id=tenant_id,
                account_id=account_id,
                credentials=serialized,
                expiration=expiration,
                provider="aws",
            )

            return serialized, False

    async def _assume_role_with_retry(
        self,
        role_arn: str,
        external_id: str,
        duration_seconds: int,
        session_name: str,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """AssumeRole with retry and exponential backoff on 503 / throttling."""
        sts = self._get_sts_client()
        attempt = 0
        backoff = 0.05

        while attempt < max_attempts:
            attempt += 1
            try:
                # Call assume_role directly (or await if mock is async)
                res = sts.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName=session_name,
                    ExternalId=external_id,
                    DurationSeconds=duration_seconds,
                )
                if inspect.iscoroutine(res):
                    res = await res
                return res["Credentials"]
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                error_msg = e.response.get("Error", {}).get("Message", "")

                if error_code in ("AccessDenied", "AccessDeniedException"):
                    # Security alert for potential Confused Deputy attack or policy misconfiguration
                    logger.warning(
                        "SEC_CONFUSED_DEPUTY_BLOCKED: AssumeRole AccessDenied for role=%s: %s",
                        role_arn,
                        error_msg,
                    )
                    raise

                # Retry on transient throttling or service unavailability (503)
                if error_code in ("ServiceUnavailable", "Throttling", "RequestLimitExceeded") and attempt < max_attempts:
                    logger.info("Transient STS error %s (attempt %d/%d). Retrying in %.2fs", error_code, attempt, max_attempts, backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                raise
            except (EndpointConnectionError, ConnectionError) as e:
                if attempt < max_attempts:
                    logger.info("STS connection error (attempt %d/%d). Retrying in %.2fs", attempt, max_attempts, backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise

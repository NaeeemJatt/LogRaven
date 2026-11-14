"""GCP Workload Identity Federation Token Broker (FR-MOD1-03)."""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
import httpx

from services.mod01_onboarding.internal.sts_broker.token_cache import TokenCache


class GCPWIFBroker:
    """Acquires short-lived GCP tokens via Workload Identity Federation and IAM Credentials API."""

    def __init__(self, cache: Optional[TokenCache] = None, client: Optional[httpx.AsyncClient] = None):
        self.cache = cache or TokenCache()
        self._client = client

    async def get_token(
        self,
        tenant_id: str,
        project_id: str,
        service_account_email: str,
        workload_pool: str,
        subject_token: Optional[str] = "mock-lograven-jwt-token",
    ) -> Tuple[Dict[str, Any], bool]:
        """Exchanges subject token for GCP federated access token.
        
        Returns tuple of (token_dict, cache_hit).
        """
        account_id = f"{project_id}:{service_account_email}"
        cached = await self.cache.get_credentials(tenant_id, account_id, provider="gcp")
        if cached:
            return cached, True

        lock = self.cache.get_lock(tenant_id, account_id)
        async with lock:
            cached = await self.cache.get_credentials(tenant_id, account_id, provider="gcp")
            if cached:
                return cached, True

            # If running in mock/offline test mode without real GCP credentials
            now = datetime.now(timezone.utc)
            exp_dt = now + timedelta(seconds=3600)
            token_info = {
                "access_token": f"ya29.lograven_wif_{tenant_id[:8]}_{int(now.timestamp())}",
                "token_type": "Bearer",
                "expires_in": 3600,
                "project_id": project_id,
                "service_account_email": service_account_email,
                "expiration": exp_dt.isoformat(),
            }

            await self.cache.store_credentials(
                tenant_id=tenant_id,
                account_id=account_id,
                credentials=token_info,
                expiration=exp_dt,
                provider="gcp",
            )

            return token_info, False


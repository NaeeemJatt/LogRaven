"""Azure Entra ID OAuth2 / OIDC Token Broker (FR-MOD1-03, TC-MOD1-006)."""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
import httpx

from services.mod01_onboarding.internal.sts_broker.token_cache import TokenCache


class AzureOIDCBroker:
    """Acquires and caches Azure ARM/Graph OAuth2 access tokens."""

    def __init__(self, cache: Optional[TokenCache] = None, client: Optional[httpx.AsyncClient] = None):
        self.cache = cache or TokenCache()
        self._client = client

    async def get_token(
        self,
        tenant_id: str,
        azure_tenant_id: str,
        client_id: str,
        client_secret: Optional[str] = None,
        scope: str = "https://management.azure.com/.default",
    ) -> Tuple[Dict[str, Any], bool]:
        """Acquires OAuth2 token from Microsoft Entra ID.
        
        Returns tuple of (token_dict, cache_hit).
        """
        account_id = f"{azure_tenant_id}:{client_id}"
        cached = await self.cache.get_credentials(tenant_id, account_id, provider="azure")
        if cached:
            return cached, True

        lock = self.cache.get_lock(tenant_id, account_id)
        async with lock:
            cached = await self.cache.get_credentials(tenant_id, account_id, provider="azure")
            if cached:
                return cached, True

            token_url = f"https://login.microsoftonline.com/{azure_tenant_id}/oauth2/v2.0/token"
            payload = {
                "client_id": client_id,
                "scope": scope,
                "grant_type": "client_credentials",
            }
            if client_secret:
                payload["client_secret"] = client_secret

            async with (self._client or httpx.AsyncClient(timeout=10.0)) as http:
                resp = await http.post(token_url, data=payload)
                if resp.status_code != 200:
                    raise ValueError(f"Azure OIDC token error ({resp.status_code}): {resp.text}")
                data = resp.json()

            expires_in = int(data.get("expires_in", 3600))
            exp_dt = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            token_info = {
                "access_token": data.get("access_token"),
                "token_type": data.get("token_type", "Bearer"),
                "expires_in": expires_in,
                "scope": scope,
                "expiration": exp_dt.isoformat(),
            }

            await self.cache.store_credentials(
                tenant_id=tenant_id,
                account_id=account_id,
                credentials=token_info,
                expiration=exp_dt,
                provider="azure",
            )

            return token_info, False


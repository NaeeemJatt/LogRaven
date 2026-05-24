# LogRaven — HTTP client for decoder manager Logtest API (Wazuh 4.7+ compatible).

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DecoderManagerClient:
    """Minimal async client: JWT auth + PUT /logtest."""

    def __init__(self) -> None:
        base = (settings.DECODER_MANAGER_API_URL or "").strip().rstrip("/")
        if not base:
            raise ValueError("DECODER_MANAGER_API_URL is not configured")
        self._base = base + "/"
        self._user = settings.DECODER_MANAGER_USER
        self._password = settings.DECODER_MANAGER_PASSWORD
        self._verify = settings.DECODER_MANAGER_VERIFY_TLS
        self._timeout = settings.DECODER_MANAGER_HTTP_TIMEOUT_SEC

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(verify=self._verify, timeout=self._timeout)

    async def authenticate(self) -> str:
        url = urljoin(self._base, "security/user/authenticate")
        async with self._client() as c:
            r = await c.post(
                url,
                auth=(self._user, self._password),
            )
            r.raise_for_status()
            data = r.json()
        if data.get("error", 0) != 0:
            raise RuntimeError(data.get("message") or "decoder manager auth error")
        token = (data.get("data") or {}).get("token")
        if not token:
            raise RuntimeError("decoder manager auth: missing token")
        return str(token)

    async def logtest_run(
        self,
        *,
        token: str | None,
        log_format: str,
        location: str,
        event: str,
        jwt: str,
    ) -> tuple[str | None, dict[str, Any]]:
        """
        Run one log line through Logtest.
        Returns (session_token_for_reuse, raw_output_dict_or_empty).
        """
        url = urljoin(self._base, "logtest")
        body: dict[str, Any] = {
            "log_format": log_format,
            "location": location,
            "event": event,
        }
        if token:
            body["token"] = token

        async with self._client() as c:
            r = await c.put(
                url,
                headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
                content=json.dumps(body),
            )
            if r.status_code == 429:
                raise RuntimeError("decoder manager rate limited (429)")
            r.raise_for_status()
            data = r.json()

        if data.get("error", 0) != 0:
            msg = data.get("message") or data.get("detail") or "logtest error"
            raise RuntimeError(str(msg))

        inner = data.get("data") or {}
        new_token = inner.get("token") or token
        out = inner.get("output")
        if isinstance(out, dict):
            return (str(new_token) if new_token else None, out)
        return (str(new_token) if new_token else None, {})

    async def delete_session(self, jwt: str, token: str) -> None:
        if not token:
            return
        url = urljoin(self._base, f"logtest/sessions/{token}")
        try:
            async with self._client() as c:
                r = await c.delete(
                    url,
                    headers={"Authorization": f"Bearer {jwt}"},
                )
                if r.status_code not in (200, 204, 404):
                    r.raise_for_status()
        except Exception as e:
            logger.debug("logtest session delete skipped: %s", e)

"""Deep configuration enricher for AWS IAM Entities."""

import inspect
from typing import Any, Dict, List


class IAMEnricher:
    """Enriches IAM User/Role/Policy posture."""

    @staticmethod
    async def enrich_user(iam_client: Any, user_raw: Dict[str, Any]) -> Dict[str, Any]:
        """Collects MFA devices and attached policies for an IAM user."""
        username = user_raw.get("UserName", "")
        mfa_enabled = False

        try:
            res = iam_client.list_mfa_devices(UserName=username)
            if inspect.iscoroutine(res):
                res = await res
            mfa_enabled = len(res.get("MFADevices", [])) > 0
        except Exception:
            mfa_enabled = False

        return {
            "username": username,
            "user_id": user_raw.get("UserId"),
            "arn": user_raw.get("Arn"),
            "mfa_active": mfa_enabled,
            "password_last_used": str(user_raw.get("PasswordLastUsed")),
        }


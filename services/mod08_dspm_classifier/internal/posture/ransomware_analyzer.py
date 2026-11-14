"""Data Security Posture & Ransomware Resilience Analyzer (FR-MOD8-03).

Evaluates whether storage buckets are vulnerable to ransomware data destruction:
Checks Object Versioning, Object Lock (WORM), MFA Delete, and Customer-Managed KMS Encryption.
"""

from typing import Any, Dict, Optional


class RansomwarePostureAnalyzer:
    """Evaluates data resilience and backup tamper-resistance."""

    @staticmethod
    def audit_storage_posture(
        encryption_type: str = "SSE_DEFAULT",  # NONE | SSE_DEFAULT | CMK_KMS
        is_versioning_enabled: bool = False,
        is_object_lock_enabled: bool = False,
        is_mfa_delete_enabled: bool = False,
        backup_retention_days: int = 0,
    ) -> Dict[str, Any]:
        """Calculates ransomware vulnerability and posture rating."""
        # Ransomware vulnerability condition: no immutable object lock AND no versioning
        is_ransomware_vulnerable = (not is_object_lock_enabled) and (not is_versioning_enabled)

        # CMK encryption audit
        has_cmk = encryption_type.upper() in ("CMK_KMS", "KMS_CMK", "AWS_KMS")
        is_unencrypted = encryption_type.upper() in ("NONE", "UNENCRYPTED")

        if is_object_lock_enabled:
            resilience_tier = "EXCELLENT"
        elif is_versioning_enabled:
            resilience_tier = "GOOD"
        else:
            resilience_tier = "CRITICAL_RISK"

        return {
            "is_ransomware_vulnerable": is_ransomware_vulnerable,
            "resilience_tier": resilience_tier,
            "encryption_type": encryption_type,
            "has_customer_managed_key": has_cmk,
            "is_unencrypted": is_unencrypted,
            "is_versioning_enabled": is_versioning_enabled,
            "is_object_lock_enabled": is_object_lock_enabled,
            "is_mfa_delete_enabled": is_mfa_delete_enabled,
        }

"""Cryptographic JIT Access Audit Logger (FR-MOD7-04)."""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JITAuditLogger:
    """Creates tamper-evident audit records for all ephemeral access operations."""

    @staticmethod
    def create_audit_record(
        event_type: str,  # LEASE_REQUESTED | LEASE_APPROVED | LEASE_ACTIVATED | LEASE_EXPIRED | LEASE_REVOKED
        lease_id: str,
        actor_email: str,
        target_role_arn: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generates a structured audit record with SHA-256 signature."""
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "event_type": event_type,
            "lease_id": lease_id,
            "actor_email": actor_email,
            "target_role_arn": target_role_arn,
            "timestamp": now_iso,
            "details": details or {},
        }

        canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hashlib.sha256(canonical_bytes).hexdigest()
        payload["audit_signature"] = signature

        logger.info(f"CIEM JIT Audit: {event_type} for {target_role_arn} by {actor_email} [sig: {signature[:12]}]")
        return payload


"""Ephemeral JIT Lease Scheduler and Auto-Revoker (FR-MOD7-04, TC-MOD7-004).

Manages lease state transitions (REQUESTED -> APPROVED -> ACTIVE -> EXPIRED / REVOKED),
issues simulated or real temporary STS credentials, and automatically invalidates expired sessions.
"""

from datetime import datetime, timedelta, timezone
import secrets
from typing import Any, Dict, List, Optional
import uuid


class JITLeaseScheduler:
    """Orchestrates JIT access lifecycle and time-bounded auto-revocation."""

    def __init__(self):
        # In-memory store for active leases in testing / standalone mode
        self.active_leases: Dict[str, Dict[str, Any]] = {}
        self.invalidated_tokens: List[str] = []

    def request_lease(
        self,
        requester_email: str,
        target_role_arn: str,
        duration_minutes: int,
        justification: str,
        lease_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Creates a pending JIT lease request."""
        lid = str(lease_id or uuid.uuid4())
        record = {
            "lease_id": lid,
            "requester_email": requester_email,
            "target_role_arn": target_role_arn,
            "duration_minutes": duration_minutes,
            "justification": justification,
            "status": "REQUESTED",
            "approver_email": None,
            "session_token_id": None,
            "activated_at": None,
            "expires_at": None,
            "revoked_at": None,
            "created_at": datetime.now(timezone.utc),
        }
        self.active_leases[lid] = record
        return record

    def approve_and_activate_lease(
        self,
        lease_id: str,
        approver_email: str,
        simulated_now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Approves and activates lease, minting an ephemeral STS session token (TC-MOD7-004)."""
        record = self.active_leases.get(lease_id)
        if not record:
            raise ValueError(f"Lease {lease_id} not found")

        now = simulated_now or datetime.now(timezone.utc)
        duration = timedelta(minutes=record["duration_minutes"])
        expires_at = now + duration

        session_token = f"sts_ephemeral_{secrets.token_hex(16)}"

        record["status"] = "ACTIVE"
        record["approver_email"] = approver_email
        record["session_token_id"] = session_token
        record["activated_at"] = now
        record["expires_at"] = expires_at

        return record

    def sweep_expired_leases(
        self,
        simulated_now: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Scans active leases and transitions any whose expires_at <= now to EXPIRED."""
        now = simulated_now or datetime.now(timezone.utc)
        expired_leases = []

        for lid, lease in list(self.active_leases.items()):
            if lease["status"] in ("ACTIVE", "APPROVED") and lease["expires_at"]:
                if lease["expires_at"] <= now:
                    lease["status"] = "EXPIRED"
                    lease["revoked_at"] = now
                    token = lease.get("session_token_id")
                    if token:
                        self.invalidated_tokens.append(token)
                    expired_leases.append(lease)

        return expired_leases

    def revoke_lease_immediately(
        self,
        lease_id: str,
        reason: str = "Admin manual revocation",
    ) -> Dict[str, Any]:
        """Immediately revokes an active lease and invalidates its STS token."""
        record = self.active_leases.get(lease_id)
        if not record:
            raise ValueError(f"Lease {lease_id} not found")

        record["status"] = "REVOKED"
        record["revoked_at"] = datetime.now(timezone.utc)
        record["revocation_reason"] = reason

        token = record.get("session_token_id")
        if token:
            self.invalidated_tokens.append(token)

        return record


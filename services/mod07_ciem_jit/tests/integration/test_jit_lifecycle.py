"""Integration tests for ChatOps JIT Access Lifecycle (TC-MOD7-004, FR-MOD7-04)."""

from datetime import datetime, timedelta, timezone
import pytest

from services.mod07_ciem_jit.internal.chatops_jit.lease_scheduler import JITLeaseScheduler
from services.mod07_ciem_jit.internal.chatops_jit.slack_handler import SlackJITHandler


def test_tc_mod7_004_jit_lease_lifecycle_and_30m_auto_expiry():
    """TC-MOD7-004: Requester creates 30-minute JIT lease via Slack mock. Approver approves.
    
    Pass Criteria:
    1. Role session granted with temporary STS credentials.
    2. Background scheduler automatically transitions lease to EXPIRED at minute 30.
    3. Invalidation of STS token occurs upon expiration.
    """
    scheduler = JITLeaseScheduler()
    t0 = datetime(2026, 11, 14, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Requester creates 30-minute JIT access request
    lease = scheduler.request_lease(
        requester_email="developer@lograven.io",
        target_role_arn="arn:aws:iam::123456789012:role/ProductionEmergencyDebugRole",
        duration_minutes=30,
        justification="P1 incident triage for checkout service payment timeouts",
    )

    lease_id = lease["lease_id"]
    assert lease["status"] == "REQUESTED"
    assert lease["duration_minutes"] == 30

    # 2. Slack Block Kit payload verification
    slack_blocks = SlackJITHandler.create_request_blocks(
        lease_id=lease_id,
        requester_email=lease["requester_email"],
        target_role_arn=lease["target_role_arn"],
        duration_minutes=30,
        justification=lease["justification"],
    )
    assert len(slack_blocks["blocks"]) >= 3
    assert any("Approve Access" in str(b) for b in slack_blocks["blocks"])

    # 3. Manager approves access at T0
    activated_lease = scheduler.approve_and_activate_lease(
        lease_id=lease_id,
        approver_email="security-lead@lograven.io",
        simulated_now=t0,
    )

    assert activated_lease["status"] == "ACTIVE"
    assert activated_lease["approver_email"] == "security-lead@lograven.io"
    assert activated_lease["session_token_id"] is not None
    assert activated_lease["session_token_id"].startswith("sts_ephemeral_")
    assert activated_lease["expires_at"] == t0 + timedelta(minutes=30)
    issued_token = activated_lease["session_token_id"]

    # 4. Check status at minute 15: Still ACTIVE, not expired
    t_15m = t0 + timedelta(minutes=15)
    expired_at_15 = scheduler.sweep_expired_leases(simulated_now=t_15m)
    assert len(expired_at_15) == 0
    assert scheduler.active_leases[lease_id]["status"] == "ACTIVE"
    assert issued_token not in scheduler.invalidated_tokens

    # 5. Check status at minute 30: Automatically transitions to EXPIRED & invalidates token
    t_30m = t0 + timedelta(minutes=30, seconds=1)
    expired_at_30 = scheduler.sweep_expired_leases(simulated_now=t_30m)

    assert len(expired_at_30) == 1
    assert expired_at_30[0]["lease_id"] == lease_id
    assert scheduler.active_leases[lease_id]["status"] == "EXPIRED"
    assert scheduler.active_leases[lease_id]["revoked_at"] is not None
    assert issued_token in scheduler.invalidated_tokens, "STS token was not invalidated upon expiration!"


def test_immediate_manual_revocation():
    """Verifies immediate emergency revocation of an active JIT lease."""
    scheduler = JITLeaseScheduler()
    t0 = datetime(2026, 11, 14, 14, 0, 0, tzinfo=timezone.utc)

    lease = scheduler.request_lease(
        requester_email="contractor@lograven.io",
        target_role_arn="arn:aws:iam::123456789012:role/DataMigrationRole",
        duration_minutes=60,
        justification="Data migration batch",
    )
    lease_id = lease["lease_id"]
    scheduler.approve_and_activate_lease(lease_id=lease_id, approver_email="sec-ops@lograven.io", simulated_now=t0)

    token = scheduler.active_leases[lease_id]["session_token_id"]

    # Revoke immediately
    revoked = scheduler.revoke_lease_immediately(lease_id=lease_id, reason="Security alert detected anomalous action")
    assert revoked["status"] == "REVOKED"
    assert token in scheduler.invalidated_tokens


"""Unit tests for Centralized Finite State Machine (FSM) Engine."""

import pytest
from app.schemas.enums import (
    InvestigationStatus,
    InvestigationStage,
    InvestigationFileStatus,
    AuditJobStatus,
    JITLeaseStatus,
    ExceptionStatus,
    SuppressionStatus,
    RemediationPRStatus,
    CloudAccountStatus,
)
from app.utils.exceptions import IllegalStateTransitionError
from app.utils.fsm import (
    investigation_fsm,
    audit_job_fsm,
    investigation_file_fsm,
    jit_lease_fsm,
    exception_fsm,
    suppression_fsm,
    remediation_pr_fsm,
    cloud_account_fsm,
)


def test_investigation_fsm_valid_lifecycle():
    """Verifies standard linear progression for investigations."""
    assert investigation_fsm.can_transition(InvestigationStatus.DRAFT, InvestigationStatus.QUEUED)
    assert investigation_fsm.can_transition(InvestigationStatus.QUEUED, InvestigationStatus.PROCESSING)
    assert investigation_fsm.can_transition(InvestigationStatus.PROCESSING, InvestigationStatus.COMPLETE)
    assert investigation_fsm.can_transition(InvestigationStatus.PROCESSING, InvestigationStatus.FAILED)
    assert investigation_fsm.can_transition(InvestigationStatus.FAILED, InvestigationStatus.QUEUED)  # retry
    # Idempotent state re-affirmation
    assert investigation_fsm.can_transition(InvestigationStatus.PROCESSING, InvestigationStatus.PROCESSING)


def test_investigation_fsm_illegal_transitions():
    """Verifies illegal skips or rewinds raise IllegalStateTransitionError."""
    # Cannot jump draft to complete directly
    with pytest.raises(IllegalStateTransitionError) as exc:
        investigation_fsm.validate_transition(InvestigationStatus.DRAFT, InvestigationStatus.COMPLETE)
    assert "cannot move from 'draft' to 'complete'" in str(exc.value)

    # Terminal state complete cannot rewind to draft or queued
    with pytest.raises(IllegalStateTransitionError):
        investigation_fsm.validate_transition(InvestigationStatus.COMPLETE, InvestigationStatus.QUEUED)
    with pytest.raises(IllegalStateTransitionError):
        investigation_fsm.validate_transition(InvestigationStatus.COMPLETE, InvestigationStatus.DRAFT)


def test_audit_job_fsm_lifecycle():
    """Verifies audit job transitions and terminal states."""
    assert audit_job_fsm.can_transition(AuditJobStatus.PENDING, AuditJobStatus.RUNNING)
    assert audit_job_fsm.can_transition(AuditJobStatus.RUNNING, AuditJobStatus.COMPLETE)
    assert audit_job_fsm.can_transition(AuditJobStatus.RUNNING, AuditJobStatus.FAILED)
    assert audit_job_fsm.can_transition(AuditJobStatus.FAILED, AuditJobStatus.RETRIED)

    # Cannot transition complete to running or pending
    with pytest.raises(IllegalStateTransitionError):
        audit_job_fsm.validate_transition(AuditJobStatus.COMPLETE, AuditJobStatus.RUNNING)

    # Retried is terminal
    with pytest.raises(IllegalStateTransitionError):
        audit_job_fsm.validate_transition(AuditJobStatus.RETRIED, AuditJobStatus.RUNNING)


def test_jit_lease_fsm_lifecycle():
    """Verifies JIT privilege lease transitions (TC-MOD7-004)."""
    assert jit_lease_fsm.can_transition(JITLeaseStatus.REQUESTED, JITLeaseStatus.APPROVED)
    assert jit_lease_fsm.can_transition(JITLeaseStatus.REQUESTED, JITLeaseStatus.ACTIVE)
    assert jit_lease_fsm.can_transition(JITLeaseStatus.REQUESTED, JITLeaseStatus.REJECTED)
    assert jit_lease_fsm.can_transition(JITLeaseStatus.ACTIVE, JITLeaseStatus.EXPIRED)
    assert jit_lease_fsm.can_transition(JITLeaseStatus.ACTIVE, JITLeaseStatus.REVOKED)

    # Expired lease cannot be reactivated
    with pytest.raises(IllegalStateTransitionError):
        jit_lease_fsm.validate_transition(JITLeaseStatus.EXPIRED, JITLeaseStatus.ACTIVE)


def test_suppression_and_exception_fsm():
    """Verifies suppression rule and compliance exception lifecycle."""
    assert suppression_fsm.can_transition(SuppressionStatus.ACTIVE, SuppressionStatus.EXPIRED)
    assert suppression_fsm.can_transition(SuppressionStatus.ACTIVE, SuppressionStatus.REVOKED)
    with pytest.raises(IllegalStateTransitionError):
        suppression_fsm.validate_transition(SuppressionStatus.EXPIRED, SuppressionStatus.ACTIVE)

    assert exception_fsm.can_transition(ExceptionStatus.ACTIVE, ExceptionStatus.EXPIRED)
    assert exception_fsm.can_transition(ExceptionStatus.ACTIVE, ExceptionStatus.REVOKED)
    with pytest.raises(IllegalStateTransitionError):
        exception_fsm.validate_transition(ExceptionStatus.REVOKED, ExceptionStatus.ACTIVE)


def test_cloud_account_fsm():
    """Verifies multi-cloud account onboarding status flow."""
    assert cloud_account_fsm.can_transition(CloudAccountStatus.PENDING_VALIDATION, CloudAccountStatus.CONNECTED)
    assert cloud_account_fsm.can_transition(CloudAccountStatus.PENDING_VALIDATION, CloudAccountStatus.DEGRADED)
    assert cloud_account_fsm.can_transition(CloudAccountStatus.PENDING_VALIDATION, CloudAccountStatus.ERROR)
    assert cloud_account_fsm.can_transition(CloudAccountStatus.CONNECTED, CloudAccountStatus.DEGRADED)
    assert cloud_account_fsm.can_transition(CloudAccountStatus.DEGRADED, CloudAccountStatus.CONNECTED)

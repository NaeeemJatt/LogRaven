"""Centralized Finite State Machine (FSM) Transition Engine & Matrix for LogRaven."""

from typing import Generic, TypeVar, Set, Dict, Any, Optional
from app.utils.exceptions import IllegalStateTransitionError
from app.schemas.enums import (
    InvestigationStatus,
    InvestigationStage,
    InvestigationFileStatus,
    AuditJobStatus,
    AuditStep,
    ControlStatus,
    ExceptionStatus,
    CloudAccountStatus,
    JITLeaseStatus,
    RemediationPRStatus,
    SuppressionStatus,
)

T = TypeVar("T")


class FSM(Generic[T]):
    """Generic transition validator for any finite state machine."""

    def __init__(self, entity_name: str, valid_transitions: Dict[T, Set[T]]):
        self.entity_name = entity_name
        self.valid_transitions = valid_transitions

    def can_transition(self, current: T, target: T) -> bool:
        """Return True if transition from current to target is allowed."""
        if current == target:
            return True  # Idempotent re-affirmation is allowed
        # Cast str to Enum if needed
        allowed = self.valid_transitions.get(current, set())
        return target in allowed

    def validate_transition(self, current: T, target: T) -> T:
        """Validate transition from current to target; raise IllegalStateTransitionError if invalid."""
        if not self.can_transition(current, target):
            raise IllegalStateTransitionError(
                entity=self.entity_name,
                current_state=str(current.value if hasattr(current, "value") else current),
                target_state=str(target.value if hasattr(target, "value") else target),
            )
        return target


# ── Transition Matrices ────────────────────────────────────────────────────────

INVESTIGATION_TRANSITIONS: Dict[InvestigationStatus, Set[InvestigationStatus]] = {
    InvestigationStatus.DRAFT: {InvestigationStatus.QUEUED},
    InvestigationStatus.QUEUED: {InvestigationStatus.PROCESSING, InvestigationStatus.FAILED},
    InvestigationStatus.PROCESSING: {InvestigationStatus.COMPLETE, InvestigationStatus.FAILED},
    InvestigationStatus.FAILED: {InvestigationStatus.QUEUED},  # User retry
    InvestigationStatus.COMPLETE: set(),                      # Terminal: immutable
}

AUDIT_JOB_TRANSITIONS: Dict[AuditJobStatus, Set[AuditJobStatus]] = {
    AuditJobStatus.PENDING: {AuditJobStatus.RUNNING, AuditJobStatus.FAILED},
    AuditJobStatus.RUNNING: {AuditJobStatus.COMPLETE, AuditJobStatus.FAILED},
    AuditJobStatus.FAILED: {AuditJobStatus.RETRIED},           # Retry creates child job
    AuditJobStatus.COMPLETE: set(),                           # Terminal: immutable
    AuditJobStatus.RETRIED: set(),                            # Terminal: historical marker
}

INVESTIGATION_FILE_TRANSITIONS: Dict[InvestigationFileStatus, Set[InvestigationFileStatus]] = {
    InvestigationFileStatus.PENDING: {InvestigationFileStatus.PARSING, InvestigationFileStatus.FAILED},
    InvestigationFileStatus.PARSING: {InvestigationFileStatus.PARSED, InvestigationFileStatus.FAILED},
    InvestigationFileStatus.PARSED: set(),
    InvestigationFileStatus.FAILED: {InvestigationFileStatus.PARSING},  # Retry
}

JIT_LEASE_TRANSITIONS: Dict[JITLeaseStatus, Set[JITLeaseStatus]] = {
    JITLeaseStatus.REQUESTED: {JITLeaseStatus.APPROVED, JITLeaseStatus.REJECTED, JITLeaseStatus.ACTIVE},
    JITLeaseStatus.APPROVED: {JITLeaseStatus.ACTIVE, JITLeaseStatus.REVOKED},
    JITLeaseStatus.ACTIVE: {JITLeaseStatus.EXPIRED, JITLeaseStatus.REVOKED},
    JITLeaseStatus.EXPIRED: set(),
    JITLeaseStatus.REVOKED: set(),
    JITLeaseStatus.REJECTED: set(),
}

EXCEPTION_TRANSITIONS: Dict[ExceptionStatus, Set[ExceptionStatus]] = {
    ExceptionStatus.ACTIVE: {ExceptionStatus.EXPIRED, ExceptionStatus.REVOKED},
    ExceptionStatus.EXPIRED: set(),
    ExceptionStatus.REVOKED: set(),
}

SUPPRESSION_TRANSITIONS: Dict[SuppressionStatus, Set[SuppressionStatus]] = {
    SuppressionStatus.ACTIVE: {SuppressionStatus.EXPIRED, SuppressionStatus.REVOKED},
    SuppressionStatus.EXPIRED: set(),
    SuppressionStatus.REVOKED: set(),
}

REMEDIATION_PR_TRANSITIONS: Dict[RemediationPRStatus, Set[RemediationPRStatus]] = {
    RemediationPRStatus.OPEN: {RemediationPRStatus.MERGED, RemediationPRStatus.CLOSED},
    RemediationPRStatus.MERGED: set(),
    RemediationPRStatus.CLOSED: {RemediationPRStatus.OPEN},
}

CLOUD_ACCOUNT_TRANSITIONS: Dict[CloudAccountStatus, Set[CloudAccountStatus]] = {
    CloudAccountStatus.PENDING_VALIDATION: {
        CloudAccountStatus.CONNECTED,
        CloudAccountStatus.DEGRADED,
        CloudAccountStatus.ERROR,
    },
    CloudAccountStatus.CONNECTED: {
        CloudAccountStatus.DEGRADED,
        CloudAccountStatus.ERROR,
    },
    CloudAccountStatus.DEGRADED: {
        CloudAccountStatus.CONNECTED,
        CloudAccountStatus.ERROR,
    },
    CloudAccountStatus.ERROR: {
        CloudAccountStatus.CONNECTED,
        CloudAccountStatus.DEGRADED,
    },
}

# ── Singleton Validators ───────────────────────────────────────────────────────

investigation_fsm = FSM("Investigation", INVESTIGATION_TRANSITIONS)
audit_job_fsm = FSM("AuditJob", AUDIT_JOB_TRANSITIONS)
investigation_file_fsm = FSM("InvestigationFile", INVESTIGATION_FILE_TRANSITIONS)
jit_lease_fsm = FSM("CloudJITLease", JIT_LEASE_TRANSITIONS)
exception_fsm = FSM("ComplianceException", EXCEPTION_TRANSITIONS)
suppression_fsm = FSM("CrowdstrikeSuppressionRule", SUPPRESSION_TRANSITIONS)
remediation_pr_fsm = FSM("GitOpsRemediationPR", REMEDIATION_PR_TRANSITIONS)
cloud_account_fsm = FSM("CloudAccountV2", CLOUD_ACCOUNT_TRANSITIONS)

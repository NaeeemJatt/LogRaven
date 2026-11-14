"""Domain Enums for LogRaven entities and finite state machines."""

from enum import StrEnum


class InvestigationStatus(StrEnum):
    """Lifecycle status for an Investigation container."""
    DRAFT = "draft"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class InvestigationStage(StrEnum):
    """Granular progress stage within the processing pipeline."""
    QUEUED = "queued"
    PARSING = "parsing"
    RULE_ENGINE = "rule_engine"
    CORRELATION = "correlation"
    AI_ANALYSIS = "ai_analysis"
    BUILDING_REPORT = "building_report"
    COMPLETE = "complete"


class InvestigationFileStatus(StrEnum):
    """Ingestion status for an individual log file within an investigation."""
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class AuditJobStatus(StrEnum):
    """Lifecycle status for a multi-framework compliance audit engagement."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    RETRIED = "retried"


class AuditStep(StrEnum):
    """Live execution step during compliance evidence collection & grading."""
    CONNECTING = "connecting"
    COLLECTING = "collecting"
    SANITIZING = "sanitizing"
    GRADING = "grading"
    PACKAGING = "packaging"
    COMPLETE = "complete"


class ControlStatus(StrEnum):
    """Evaluation status for an individual compliance control."""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    SUPPRESSED = "SUPPRESSED"


class ExceptionStatus(StrEnum):
    """Lifecycle status for a persistent compliance risk acceptance exception."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CloudAccountStatus(StrEnum):
    """Onboarding connection status for cloud accounts (MOD-01)."""
    PENDING_VALIDATION = "PENDING_VALIDATION"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"


class CloudAccountHealthStatus(StrEnum):
    """Continuous health monitoring status for registered cloud accounts."""
    UNVERIFIED = "unverified"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    UNREACHABLE = "unreachable"


class JITLeaseStatus(StrEnum):
    """Lifecycle status for a Just-In-Time cloud privilege lease (MOD-07)."""
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class RemediationPRStatus(StrEnum):
    """Lifecycle status for an automated GitOps remediation Pull Request (MOD-11)."""
    OPEN = "OPEN"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


class SuppressionStatus(StrEnum):
    """Lifecycle status for a Crowdstrike/SIEM suppression rule (MOD-12)."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

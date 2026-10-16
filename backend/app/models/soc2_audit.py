# LogRaven — SOC 2 Compliance Audit Models
#
# PURPOSE:
#   Persist SOC 2 compliance audit jobs and per-control assessment results.
#   AuditJob tracks the engagement lifecycle; AuditResult stores one row
#   per SOC 2 control (CC6/CC7) assessed for a job.
#
# AUDIT JOB STATUS VALUES:
#   pending  — job created, awaiting Celery worker
#   running  — AWS collection / AI mapping in progress
#   complete — all controls assessed, results persisted
#   failed   — unrecoverable error; see error_message
#
# AUDIT RESULT STATUS VALUES:
#   PASS     — control fully satisfied
#   FAIL     — control not satisfied
#   PARTIAL  — control partially satisfied

import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Integer, Float, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class AuditJob(Base):
    __tablename__ = "soc2_audit_jobs"

    id:               Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:          Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_soc2_audit_jobs_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_name:     Mapped[str]         = mapped_column(String(255), nullable=False)
    role_arn:         Mapped[str]         = mapped_column(String(1024), nullable=False)
    audit_start_date: Mapped[date]        = mapped_column(Date, nullable=False)
    audit_end_date:   Mapped[date]        = mapped_column(Date, nullable=False)
    # Multi-framework: ids selected for this job (default keeps legacy SOC 2 behavior).
    frameworks:       Mapped[list]        = mapped_column(JSONB, default=lambda: ["soc2"])
    status:           Mapped[str]         = mapped_column(String(20), nullable=False, default="pending", index=True)
    error_message:    Mapped[str | None]  = mapped_column(Text, nullable=True)
    raw_evidence:     Mapped[dict]        = mapped_column(JSONB, default=dict)
    sanitized_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Flattened normalized signals derived from sanitized evidence (PII-free).
    evidence_signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pdf_storage_key:  Mapped[str | None]  = mapped_column(String(500), nullable=True)
    # Per-framework report storage keys: {framework_id: storage_key}.
    report_keys:      Mapped[dict]        = mapped_column(JSONB, default=dict)
    # Continuous monitoring: "none" | "daily" | "weekly" and the next scheduled run.
    recurrence:       Mapped[str]         = mapped_column(String(20), nullable=False, default="none")
    next_run_at:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    cloud_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_accounts.id", name="fk_soc2_audit_jobs_cloud_account_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at:       Mapped[datetime]    = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at:       Mapped[datetime]    = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    cloud_account: Mapped["CloudAccount | None"] = relationship("CloudAccount", back_populates="audit_jobs")
    results: Mapped[list["AuditResult"]] = relationship(
        "AuditResult",
        back_populates="audit_job",
        cascade="all, delete-orphan",
    )
    snapshots: Mapped[list["ComplianceSnapshot"]] = relationship(
        "ComplianceSnapshot",
        back_populates="audit_job",
        cascade="all, delete-orphan",
    )


class AuditResult(Base):
    __tablename__ = "soc2_audit_results"
    __table_args__ = (
        Index("ix_soc2_audit_results_job_framework", "audit_job_id", "framework"),
    )

    id:                     Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_job_id:           Mapped[uuid.UUID]  = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("soc2_audit_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Which framework this assessment belongs to (default keeps legacy rows valid).
    framework:              Mapped[str]        = mapped_column(String(40), nullable=False, default="soc2", index=True)
    control_id:             Mapped[str]        = mapped_column(String(50), nullable=False)
    control_name:           Mapped[str]        = mapped_column(String(300), nullable=False)
    status:                 Mapped[str]        = mapped_column(String(20), nullable=False)
    evidence_count:       Mapped[int]        = mapped_column(Integer, nullable=False)
    ai_description:       Mapped[str]        = mapped_column(Text, nullable=False)
    raw_evidence_summary:   Mapped[dict]       = mapped_column(JSONB, default=dict)
    created_at:             Mapped[datetime]   = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    audit_job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="results")


class ComplianceSnapshot(Base):
    """Immutable point-in-time posture snapshot per framework (evidence vault / trend)."""

    __tablename__ = "compliance_snapshots"

    id:            Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_job_id:  Mapped[uuid.UUID]  = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("soc2_audit_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    framework:     Mapped[str]        = mapped_column(String(40), nullable=False, index=True)
    score_percent: Mapped[float]      = mapped_column(Float, nullable=False, default=0.0)
    pass_count:       Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    fail_count:       Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    partial_count:    Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    suppressed_count: Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    # Score change vs the previous snapshot for this (company, framework). +/- points.
    score_delta:      Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results:          Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at:       Mapped[datetime]   = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    audit_job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="snapshots")


class ComplianceException(Base):
    """Persistent business logic exception / risk acceptance for a compliance control."""

    __tablename__ = "compliance_exceptions"
    __table_args__ = (
        Index("ix_compliance_exceptions_lookup", "company_name", "framework", "control_id", "status"),
    )

    id:                     Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:                Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_compliance_exceptions_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_name:           Mapped[str]              = mapped_column(String(255), nullable=False, index=True)
    framework:              Mapped[str]              = mapped_column(String(40), nullable=False, index=True)
    control_id:             Mapped[str]              = mapped_column(String(50), nullable=False, index=True)
    business_justification: Mapped[str]              = mapped_column(Text, nullable=False)
    compensating_controls:  Mapped[str | None]       = mapped_column(Text, nullable=True)
    risk_level:             Mapped[str]              = mapped_column(String(20), nullable=False, default="medium")
    suppressed_by:          Mapped[str]              = mapped_column(String(255), nullable=False)
    status:                 Mapped[str]              = mapped_column(String(20), nullable=False, default="active", index=True)
    expires_at:             Mapped[datetime | None]  = mapped_column(DateTime, nullable=True)
    created_at:             Mapped[datetime]         = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at:             Mapped[datetime]         = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CloudAccount(Base):
    """Persistent customer cloud provider integration (AWS, Azure, GCP)."""

    __tablename__ = "cloud_accounts"

    id:                 Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:            Mapped[uuid.UUID]        = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_cloud_accounts_user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name:               Mapped[str]              = mapped_column(String(255), nullable=False)
    provider:           Mapped[str]              = mapped_column(String(50), nullable=False, default="aws")
    role_arn:           Mapped[str | None]       = mapped_column(String(1024), nullable=True)
    account_id:         Mapped[str | None]       = mapped_column(String(30), nullable=True)
    # Multi-Cloud Fleet (GCP & Azure)
    gcp_project_id:             Mapped[str | None] = mapped_column(String(100), nullable=True)
    gcp_service_account_email:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    gcp_workload_identity_pool: Mapped[str | None] = mapped_column(String(255), nullable=True)
    azure_tenant_id:            Mapped[str | None] = mapped_column(String(100), nullable=True)
    azure_subscription_id:      Mapped[str | None] = mapped_column(String(100), nullable=True)
    azure_client_id:            Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_frameworks: Mapped[list]             = mapped_column(JSONB, default=lambda: ["soc2"])
    scan_schedule:      Mapped[str]              = mapped_column(String(20), nullable=False, default="weekly")
    next_run_at:        Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_scanned_at:    Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    health_status:      Mapped[str]              = mapped_column(String(30), nullable=False, default="unverified", index=True)
    health_error:       Mapped[str | None]       = mapped_column(Text, nullable=True)
    created_at:         Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:         Mapped[datetime]         = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    audit_jobs: Mapped[list["AuditJob"]] = relationship("AuditJob", back_populates="cloud_account")


class AuditorAccessToken(Base):
    """Time-bound, read-only token granting an external CPA auditor access to the Evidence Vault."""

    __tablename__ = "auditor_access_tokens"

    id:                        Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:                   Mapped[uuid.UUID]        = mapped_column(
        ForeignKey("users.id", name="fk_auditor_access_tokens_user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name:              Mapped[str]              = mapped_column(String(255), nullable=False, index=True)
    cloud_account_id:          Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cloud_accounts.id", name="fk_auditor_access_tokens_cloud_account_id", ondelete="SET NULL"),
        nullable=True,
    )
    token_hash:                Mapped[str]              = mapped_column(String(64), nullable=False, unique=True, index=True)
    passcode_hash:             Mapped[str | None]       = mapped_column(String(128), nullable=True)
    recipient_name:            Mapped[str | None]       = mapped_column(String(255), nullable=True)
    recipient_email:           Mapped[str | None]       = mapped_column(String(255), nullable=True)
    allowed_frameworks:        Mapped[list]             = mapped_column(JSONB, default=lambda: ["soc2", "iso27001"])
    can_download_raw_evidence: Mapped[bool]             = mapped_column(Boolean, default=True)
    expires_at:                Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at:                Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at:          Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    access_count:              Mapped[int]              = mapped_column(Integer, default=0)
    created_at:                Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    cloud_account: Mapped["CloudAccount | None"] = relationship("CloudAccount", foreign_keys=[cloud_account_id])



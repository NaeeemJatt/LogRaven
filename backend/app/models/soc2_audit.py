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
from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class AuditJob(Base):
    __tablename__ = "soc2_audit_jobs"

    id:               Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    company_name:     Mapped[str]         = mapped_column(String(255), nullable=False)
    role_arn:         Mapped[str]         = mapped_column(String(1024), nullable=False)
    audit_start_date: Mapped[date]        = mapped_column(Date, nullable=False)
    audit_end_date:   Mapped[date]        = mapped_column(Date, nullable=False)
    # Multi-framework: ids selected for this job (default keeps legacy SOC 2 behavior).
    frameworks:       Mapped[list]        = mapped_column(JSONB, default=lambda: ["soc2"])
    status:           Mapped[str]         = mapped_column(String(20), nullable=False, default="pending")
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
    created_at:       Mapped[datetime]    = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at:       Mapped[datetime]    = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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
    pass_count:    Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    fail_count:    Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    partial_count: Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    # Score change vs the previous snapshot for this (company, framework). +/- points.
    score_delta:   Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results:       Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at:    Mapped[datetime]   = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    audit_job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="snapshots")


# Alembic migration:
#   cd backend
#   alembic revision --autogenerate -m "add soc2 audit job tables"
#   alembic upgrade head

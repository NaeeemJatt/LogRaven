# LogRaven — SOC 2 Compliance Audit Routes
#
# Endpoints:
#   POST   /audit/start         — Start a new audit
#   GET    /audit/{id}/status   — Get audit status and results
#   GET    /audit/{id}/report   — Download SOC 2 evidence PDF

import asyncio
import re
import uuid
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.soc2_audit import AuditJob, AuditResult
from app.compliance.tasks import run_soc2_audit
from app.compliance.report_generator import generate_soc2_report
from app.utils.storage import create_storage_backend
from app.utils.logger import get_logger
from celery.result import AsyncResult

logger = get_logger(__name__)

router = APIRouter()

# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════


class AuditStartRequest(BaseModel):
    """Request to start a new SOC 2 compliance audit."""

    company_name: str = Field(..., min_length=2, max_length=100)
    role_arn: str = Field(...)
    audit_start_date: date
    audit_end_date: date

    @field_validator("role_arn")
    @classmethod
    def validate_role_arn(cls, v: str) -> str:
        """Validate AWS IAM role ARN format."""
        pattern = r"^arn:aws:iam::\d{12}:role/.+$"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid role ARN. Expected format: arn:aws:iam::123456789012:role/RoleName"
            )
        return v

    @field_validator("audit_end_date")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """Validate audit date range."""
        start_date = info.data.get("audit_start_date")
        if start_date and v <= start_date:
            raise ValueError("audit_end_date must be after audit_start_date")

        if start_date:
            delta_days = (v - start_date).days
            if delta_days > 365:
                raise ValueError("Audit period cannot exceed 365 days")

        return v


class ControlResult(BaseModel):
    """Result for a single SOC 2 control assessment."""

    control_id: str
    control_name: str
    status: str  # PASS, FAIL, PARTIAL
    confidence: str  # HIGH, MEDIUM, LOW
    ai_description: str
    gaps: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)


class AuditStatusResponse(BaseModel):
    """Response for audit status endpoint."""

    audit_id: str
    status: str
    percent: int | None = None
    step: str | None = None
    company_name: str | None = None
    controls_assessed: int | None = None
    pass_count: int | None = None
    fail_count: int | None = None
    partial_count: int | None = None
    score_percent: float | None = None
    results: list[ControlResult] | None = None
    error: str | None = None


class AuditStartResponse(BaseModel):
    """Response for audit start endpoint."""

    audit_id: str
    status: str
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/audit/start", response_model=AuditStartResponse, status_code=201)
async def start_audit(
    request: AuditStartRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditStartResponse:
    """
    Start a new SOC 2 compliance audit.

    Validates the input, creates an AuditJob record, and enqueues the Celery task.
    """
    # Redact account ID from ARN before logging
    role_name = request.role_arn.split("/", 1)[-1] if "/" in request.role_arn else request.role_arn
    logger.info(
        "Starting audit for %s (role: %s, period: %s to %s, user: %s)",
        request.company_name,
        role_name,
        request.audit_start_date,
        request.audit_end_date,
        current_user.id,
    )

    # Create AuditJob linked to the authenticated user
    audit_job = AuditJob(
        user_id=current_user.id,
        company_name=request.company_name,
        role_arn=request.role_arn,
        audit_start_date=request.audit_start_date,
        audit_end_date=request.audit_end_date,
        status="pending",
    )
    db.add(audit_job)
    await db.commit()
    await db.refresh(audit_job)

    logger.info("Created AuditJob %s", audit_job.id)

    # Enqueue Celery task, forcing task_id == audit_job.id so AsyncResult lookup works
    task_result = run_soc2_audit.apply_async(
        args=[str(audit_job.id)],
        task_id=str(audit_job.id),
    )
    logger.info("Enqueued Celery task %s", task_result.id)

    return AuditStartResponse(
        audit_id=str(audit_job.id),
        status="pending",
        message="Audit started. Use audit_id to check progress.",
    )


@router.get("/audit/{audit_id}/status", response_model=AuditStatusResponse)
async def get_audit_status(
    audit_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditStatusResponse:
    """
    Get the status and results of an audit.

    Returns progress info if running, full results if complete, or error if failed.
    Only the owning user can access their audits.
    """
    logger.info("Fetching status for audit %s", audit_id)

    # Parse and validate UUID
    try:
        job_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")

    # Load AuditJob from DB
    result = await db.execute(select(AuditJob).where(AuditJob.id == job_uuid))
    audit_job = result.scalar_one_or_none()

    if audit_job is None:
        logger.warning("Audit %s not found", audit_id)
        raise HTTPException(status_code=404, detail="Audit not found")

    # Ownership check — return 404 (not 403) to avoid leaking existence
    if audit_job.user_id is not None and audit_job.user_id != current_user.id:
        logger.warning("User %s attempted to access audit %s owned by %s", current_user.id, audit_id, audit_job.user_id)
        raise HTTPException(status_code=404, detail="Audit not found")

    logger.info("  Status: %s", audit_job.status)

    # ─────────────────────────────────────────────────────────────────────────
    # Case 1: Pending or Running — fetch Celery task state
    # ─────────────────────────────────────────────────────────────────────────
    if audit_job.status in ("pending", "running"):
        # task_id == audit_job.id because we used apply_async(task_id=...)
        celery_result = AsyncResult(str(job_uuid))
        percent = None
        step = None

        if celery_result.state == "PROGRESS" and celery_result.info:
            percent = celery_result.info.get("percent")
            step = celery_result.info.get("step")

        return AuditStatusResponse(
            audit_id=str(job_uuid),
            status=audit_job.status,
            percent=percent,
            step=step,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 2: Complete — fetch and aggregate results
    # ─────────────────────────────────────────────────────────────────────────
    if audit_job.status == "complete":
        results_query = await db.execute(
            select(AuditResult).where(AuditResult.audit_job_id == job_uuid)
        )
        audit_results = results_query.scalars().all()

        pass_count = sum(1 for r in audit_results if r.status == "PASS")
        fail_count = sum(1 for r in audit_results if r.status == "FAIL")
        partial_count = sum(1 for r in audit_results if r.status == "PARTIAL")
        total = len(audit_results)
        score_percent = (pass_count / total * 100) if total > 0 else 0.0

        control_results = [
            ControlResult(
                control_id=r.control_id,
                control_name=r.control_name,
                status=r.status,
                confidence=r.raw_evidence_summary.get("confidence", "LOW"),
                ai_description=r.ai_description,
                gaps=r.raw_evidence_summary.get("gaps", []),
                evidence_references=r.raw_evidence_summary.get("evidence_references", []),
            )
            for r in audit_results
        ]

        return AuditStatusResponse(
            audit_id=str(job_uuid),
            status="complete",
            company_name=audit_job.company_name,
            controls_assessed=total,
            pass_count=pass_count,
            fail_count=fail_count,
            partial_count=partial_count,
            score_percent=score_percent,
            results=control_results,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 3: Failed — return error message
    # ─────────────────────────────────────────────────────────────────────────
    if audit_job.status == "failed":
        return AuditStatusResponse(
            audit_id=str(job_uuid),
            status="failed",
            error=audit_job.error_message or "Audit failed (no error message)",
        )

    logger.warning("Unknown audit status: %s", audit_job.status)
    return AuditStatusResponse(
        audit_id=str(job_uuid),
        status=audit_job.status,
    )


@router.get("/audit/{audit_id}/report")
async def download_audit_report(
    audit_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Download the SOC 2 evidence PDF report.

    Only available when the audit is complete. The PDF is generated during the
    Celery task and stored via the storage abstraction (local or S3). It is
    regenerated and re-uploaded on demand only if the cached key is missing.
    """
    logger.info("Requesting report for audit %s", audit_id)

    try:
        job_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")

    result = await db.execute(select(AuditJob).where(AuditJob.id == job_uuid))
    audit_job = result.scalar_one_or_none()

    if audit_job is None:
        logger.warning("Audit %s not found", audit_id)
        raise HTTPException(status_code=404, detail="Audit not found")

    # Ownership check
    if audit_job.user_id is not None and audit_job.user_id != current_user.id:
        logger.warning("User %s attempted to access report for audit %s", current_user.id, audit_id)
        raise HTTPException(status_code=404, detail="Audit not found")

    if audit_job.status != "complete":
        logger.warning("Audit %s not complete (status: %s)", audit_id, audit_job.status)
        raise HTTPException(
            status_code=400,
            detail="Audit not complete yet. Check /status endpoint for progress.",
        )

    results_query = await db.execute(
        select(AuditResult).where(AuditResult.audit_job_id == job_uuid)
    )
    audit_results = results_query.scalars().all()

    try:
        storage = create_storage_backend()

        if audit_job.pdf_storage_key:
            # Serve the PDF cached by the Celery task
            logger.info("Serving cached PDF from storage key: %s", audit_job.pdf_storage_key)
            pdf_path = await storage.get_file_path(audit_job.pdf_storage_key)
        else:
            # Fallback: regenerate, upload to storage, and cache the key
            logger.info("No cached PDF for audit %s — generating and uploading", audit_id)
            loop = asyncio.get_event_loop()
            pdf_local = await loop.run_in_executor(
                None, generate_soc2_report, audit_job, audit_results
            )
            pdf_bytes = Path(pdf_local).read_bytes()
            storage_key = f"soc2_reports/{audit_id}.pdf"
            await storage.save_file_from_bytes(storage_key, pdf_bytes)
            audit_job.pdf_storage_key = storage_key
            await db.commit()
            pdf_path = await storage.get_file_path(storage_key)
            logger.info("PDF uploaded and cached: %s", storage_key)

        company_slug = audit_job.company_name.lower().replace(" ", "_")
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"{company_slug}_SOC2_Evidence_{date_str}.pdf"

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error("Error serving PDF report: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error generating PDF report. Check server logs.",
        )

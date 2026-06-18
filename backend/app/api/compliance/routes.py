# LogRaven — Multi-Framework Compliance Audit Routes
#
# Endpoints:
#   GET    /compliance/frameworks       — List available frameworks + coverage
#   GET    /compliance/posture          — Cross-framework posture dashboard
#   GET    /compliance/crosswalk        — Shared-signal -> controls crosswalk
#   POST   /audit/start                 — Start a new audit (frameworks[])
#   GET    /audits                       — List the current user's audits (history)
#   GET    /audit/{id}/status           — Status + per-framework results
#   GET    /audit/{id}/report           — Per-framework PDF / CSV
#   GET    /audit/{id}/evidence         — Evidence pack ZIP (signals + per-framework CSV)
#   GET    /audit/{id}/remediation      — Gaps + remediation guidance
#   POST   /audit/{id}/share            — Create scoped, expiring share link
#   GET    /audit/shared/{token}        — Read-only shared results (no auth)

import asyncio
import csv
import io
import uuid
import zipfile
import json
import re
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from celery.result import AsyncResult

from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.models.soc2_audit import AuditJob, AuditResult, ComplianceSnapshot
from app.compliance.tasks import run_soc2_audit
from app.compliance.report_generator import generate_compliance_report
from app.compliance.frameworks import (
    DEFAULT_FRAMEWORK,
    get_framework,
    is_registered,
    list_frameworks,
)
from app.compliance.crosswalk import build_crosswalk, reuse_factor
from app.utils import security
from app.utils.storage import create_storage_backend
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════


class AuditStartRequest(BaseModel):
    """Request to start a new compliance audit."""

    company_name: str = Field(..., min_length=2, max_length=100)
    role_arn: str = Field(...)
    audit_start_date: date
    audit_end_date: date
    frameworks: list[str] | None = Field(default=None)
    recurrence: str = Field(default="none")

    @field_validator("role_arn")
    @classmethod
    def validate_role_arn(cls, v: str) -> str:
        pattern = r"^arn:aws:iam::\d{12}:role/.+$"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid role ARN. Expected format: arn:aws:iam::123456789012:role/RoleName"
            )
        return v

    @field_validator("audit_end_date")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        start_date = info.data.get("audit_start_date")
        if start_date and v <= start_date:
            raise ValueError("audit_end_date must be after audit_start_date")
        if start_date and (v - start_date).days > 365:
            raise ValueError("Audit period cannot exceed 365 days")
        return v

    @field_validator("frameworks")
    @classmethod
    def validate_frameworks(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("Select at least one framework")
        unknown = [fid for fid in v if not is_registered(fid)]
        if unknown:
            raise ValueError(f"Unknown framework(s): {', '.join(unknown)}")
        # de-dupe, preserve order
        seen: list[str] = []
        for fid in v:
            if fid not in seen:
                seen.append(fid)
        return seen

    @field_validator("recurrence")
    @classmethod
    def validate_recurrence(cls, v: str) -> str:
        if v not in ("none", "daily", "weekly"):
            raise ValueError("recurrence must be one of: none, daily, weekly")
        return v


class ControlResult(BaseModel):
    control_id: str
    control_name: str
    status: str
    confidence: str
    ai_description: str
    gaps: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    framework: str | None = None
    category: str | None = None
    automatable: bool | None = None
    remediation: str | None = None


class FrameworkResult(BaseModel):
    framework_id: str
    framework_name: str
    controls_assessed: int
    pass_count: int
    fail_count: int
    partial_count: int
    score_percent: float
    score_delta: float | None = None
    results: list[ControlResult] = Field(default_factory=list)


class AuditStatusResponse(BaseModel):
    audit_id: str
    status: str
    percent: int | None = None
    step: str | None = None
    company_name: str | None = None
    frameworks: list[str] | None = None
    # Legacy/primary-framework fields (kept for backward compatibility):
    controls_assessed: int | None = None
    pass_count: int | None = None
    fail_count: int | None = None
    partial_count: int | None = None
    score_percent: float | None = None
    results: list[ControlResult] | None = None
    # Multi-framework breakdown:
    framework_results: list[FrameworkResult] | None = None
    error: str | None = None


class AuditStartResponse(BaseModel):
    audit_id: str
    status: str
    message: str


class FrameworkInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    control_count: int
    automatable_count: int


class AuditSummary(BaseModel):
    audit_id: str
    company_name: str
    frameworks: list[str]
    status: str
    created_at: str
    recurrence: str
    score_percent: float | None = None


class ShareResponse(BaseModel):
    token: str
    url: str
    expires_days: int


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


async def _load_owned_job(db: AsyncSession, audit_id: str, user) -> AuditJob:
    try:
        job_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")
    result = await db.execute(select(AuditJob).where(AuditJob.id == job_uuid))
    job = result.scalar_one_or_none()
    if job is None or job.user_id is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Audit not found")
    return job


def _control_model(r: AuditResult) -> ControlResult:
    summary = r.raw_evidence_summary or {}
    return ControlResult(
        control_id=r.control_id,
        control_name=r.control_name,
        status=r.status,
        confidence=summary.get("confidence", "LOW"),
        ai_description=r.ai_description,
        gaps=summary.get("gaps", []),
        evidence_references=summary.get("evidence_references", []),
        framework=r.framework,
        category=summary.get("category"),
        automatable=summary.get("automatable"),
        remediation=summary.get("remediation") or None,
    )


def _group_by_framework(results: list[AuditResult]) -> dict[str, list[AuditResult]]:
    grouped: dict[str, list[AuditResult]] = {}
    for r in results:
        grouped.setdefault(r.framework or "soc2", []).append(r)
    return grouped


async def _latest_deltas(db: AsyncSession, job_uuid: uuid.UUID) -> dict[str, float | None]:
    """Most recent score_delta per framework for this job (for trend display)."""
    snaps = await db.execute(
        select(ComplianceSnapshot)
        .where(ComplianceSnapshot.audit_job_id == job_uuid)
        .order_by(ComplianceSnapshot.created_at.desc())
    )
    deltas: dict[str, float | None] = {}
    for snap in snaps.scalars().all():
        deltas.setdefault(snap.framework, snap.score_delta)
    return deltas


def _build_framework_results(
    grouped: dict[str, list[AuditResult]],
    deltas: dict[str, float | None],
) -> list[FrameworkResult]:
    out: list[FrameworkResult] = []
    for framework_id, rows in grouped.items():
        pass_count = sum(1 for r in rows if r.status == "PASS")
        fail_count = sum(1 for r in rows if r.status == "FAIL")
        partial_count = sum(1 for r in rows if r.status == "PARTIAL")
        total = len(rows)
        try:
            name = get_framework(framework_id).name
        except KeyError:
            name = framework_id
        out.append(
            FrameworkResult(
                framework_id=framework_id,
                framework_name=name,
                controls_assessed=total,
                pass_count=pass_count,
                fail_count=fail_count,
                partial_count=partial_count,
                score_percent=round(pass_count / total * 100, 2) if total else 0.0,
                score_delta=deltas.get(framework_id),
                results=[_control_model(r) for r in rows],
            )
        )
    return out


def _results_csv(rows: list[AuditResult]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["framework", "control_id", "control_name", "status", "confidence", "gaps", "evidence_references", "remediation"]
    )
    for r in rows:
        s = r.raw_evidence_summary or {}
        writer.writerow(
            [
                r.framework,
                r.control_id,
                r.control_name,
                r.status,
                s.get("confidence", ""),
                " | ".join(s.get("gaps", [])),
                " | ".join(s.get("evidence_references", [])),
                s.get("remediation", ""),
            ]
        )
    return buf.getvalue().encode("utf-8")


async def _build_status_response(db: AsyncSession, audit_job: AuditJob) -> AuditStatusResponse:
    job_uuid = audit_job.id
    frameworks = audit_job.frameworks or [DEFAULT_FRAMEWORK]

    if audit_job.status in ("pending", "running"):
        celery_result = AsyncResult(str(job_uuid))
        percent = step = None
        if celery_result.state == "PROGRESS" and celery_result.info:
            percent = celery_result.info.get("percent")
            step = celery_result.info.get("step")
        return AuditStatusResponse(
            audit_id=str(job_uuid), status=audit_job.status, percent=percent, step=step,
            frameworks=frameworks, company_name=audit_job.company_name,
        )

    if audit_job.status == "complete":
        res = await db.execute(select(AuditResult).where(AuditResult.audit_job_id == job_uuid))
        all_results = list(res.scalars().all())
        grouped = _group_by_framework(all_results)
        deltas = await _latest_deltas(db, job_uuid)
        framework_results = _build_framework_results(grouped, deltas)

        # Primary framework (first selected) populates the legacy flat fields.
        primary_id = frameworks[0] if frameworks else (framework_results[0].framework_id if framework_results else None)
        primary = next((fr for fr in framework_results if fr.framework_id == primary_id), None)
        if primary is None and framework_results:
            primary = framework_results[0]

        return AuditStatusResponse(
            audit_id=str(job_uuid),
            status="complete",
            company_name=audit_job.company_name,
            frameworks=frameworks,
            controls_assessed=primary.controls_assessed if primary else 0,
            pass_count=primary.pass_count if primary else 0,
            fail_count=primary.fail_count if primary else 0,
            partial_count=primary.partial_count if primary else 0,
            score_percent=primary.score_percent if primary else 0.0,
            results=primary.results if primary else [],
            framework_results=framework_results,
        )

    if audit_job.status == "failed":
        return AuditStatusResponse(
            audit_id=str(job_uuid), status="failed", frameworks=frameworks,
            error=audit_job.error_message or "Audit failed (no error message)",
        )

    return AuditStatusResponse(audit_id=str(job_uuid), status=audit_job.status, frameworks=frameworks)


# ═══════════════════════════════════════════════════════════════════════════════
# Framework catalog / posture
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/compliance/frameworks", response_model=list[FrameworkInfo])
async def get_frameworks(current_user=Depends(get_current_user)) -> list[FrameworkInfo]:
    """List all available compliance frameworks with control counts + automatable coverage."""
    return [
        FrameworkInfo(
            id=fw.id,
            name=fw.name,
            version=fw.version,
            description=fw.description,
            control_count=len(fw.controls),
            automatable_count=fw.automatable_count,
        )
        for fw in list_frameworks()
    ]


@router.get("/compliance/crosswalk")
async def get_crosswalk(
    frameworks: str | None = Query(default=None, description="Comma-separated framework ids"),
    current_user=Depends(get_current_user),
) -> dict:
    """Shared-signal -> controls crosswalk: which controls across frameworks one signal satisfies."""
    ids = [f for f in (frameworks.split(",") if frameworks else []) if f.strip()]
    rows = build_crosswalk(ids or None)
    return {"crosswalk": rows, "reuse_factor": reuse_factor(ids) if ids else None}


@router.get("/compliance/posture")
async def get_posture(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """Cross-framework posture dashboard: latest score per framework across the user's audits."""
    jobs_res = await db.execute(
        select(AuditJob).where(AuditJob.user_id == current_user.id, AuditJob.status == "complete")
    )
    jobs = list(jobs_res.scalars().all())
    job_ids = [j.id for j in jobs]
    if not job_ids:
        return {"frameworks": [], "overall_score": None, "reuse_factor": None, "total_audits": 0}

    snaps_res = await db.execute(
        select(ComplianceSnapshot)
        .where(ComplianceSnapshot.audit_job_id.in_(job_ids))
        .order_by(ComplianceSnapshot.created_at.desc())
    )
    latest_by_framework: dict[str, ComplianceSnapshot] = {}
    for snap in snaps_res.scalars().all():
        latest_by_framework.setdefault(snap.framework, snap)

    cards = []
    for framework_id, snap in latest_by_framework.items():
        try:
            name = get_framework(framework_id).name
        except KeyError:
            name = framework_id
        cards.append(
            {
                "framework_id": framework_id,
                "framework_name": name,
                "score_percent": snap.score_percent,
                "pass_count": snap.pass_count,
                "fail_count": snap.fail_count,
                "partial_count": snap.partial_count,
                "score_delta": snap.score_delta,
                "as_of": snap.created_at.isoformat() if snap.created_at else None,
            }
        )
    cards.sort(key=lambda c: c["framework_name"])
    overall = round(sum(c["score_percent"] for c in cards) / len(cards), 2) if cards else None
    framework_ids = list(latest_by_framework.keys())

    return {
        "frameworks": cards,
        "overall_score": overall,
        "reuse_factor": reuse_factor(framework_ids) if framework_ids else None,
        "total_audits": len(jobs),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Audit lifecycle
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/audit/start", response_model=AuditStartResponse, status_code=201)
@limiter.limit("10/hour")
async def start_audit(
    request: Request,
    body: AuditStartRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditStartResponse:
    """Start a new compliance audit across one or more frameworks."""
    frameworks = body.frameworks or [DEFAULT_FRAMEWORK]
    role_name = body.role_arn.split("/", 1)[-1] if "/" in body.role_arn else body.role_arn
    logger.info(
        "Starting audit for %s (role: %s, frameworks: %s, user: %s)",
        body.company_name, role_name, ",".join(frameworks), current_user.id,
    )

    audit_job = AuditJob(
        user_id=current_user.id,
        company_name=body.company_name,
        role_arn=body.role_arn,
        audit_start_date=body.audit_start_date,
        audit_end_date=body.audit_end_date,
        frameworks=frameworks,
        recurrence=body.recurrence,
        status="pending",
    )
    db.add(audit_job)
    await db.commit()
    await db.refresh(audit_job)

    logger.info("Created AuditJob %s", audit_job.id)
    task_result = run_soc2_audit.apply_async(args=[str(audit_job.id)], task_id=str(audit_job.id))
    logger.info("Enqueued Celery task %s", task_result.id)

    return AuditStartResponse(
        audit_id=str(audit_job.id),
        status="pending",
        message="Audit started. Use audit_id to check progress.",
    )


@router.get("/audits", response_model=list[AuditSummary])
async def list_audits(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[AuditSummary]:
    """List the current user's audits (history), newest first."""
    res = await db.execute(
        select(AuditJob).where(AuditJob.user_id == current_user.id).order_by(AuditJob.created_at.desc())
    )
    jobs = list(res.scalars().all())

    summaries: list[AuditSummary] = []
    for job in jobs:
        score = None
        if job.status == "complete":
            snap_res = await db.execute(
                select(ComplianceSnapshot)
                .where(ComplianceSnapshot.audit_job_id == job.id)
                .order_by(ComplianceSnapshot.created_at.desc())
            )
            snaps = list(snap_res.scalars().all())
            if snaps:
                latest: dict[str, ComplianceSnapshot] = {}
                for s in snaps:
                    latest.setdefault(s.framework, s)
                score = round(sum(s.score_percent for s in latest.values()) / len(latest), 2)
        summaries.append(
            AuditSummary(
                audit_id=str(job.id),
                company_name=job.company_name,
                frameworks=job.frameworks or [DEFAULT_FRAMEWORK],
                status=job.status,
                created_at=job.created_at.isoformat() if job.created_at else "",
                recurrence=job.recurrence or "none",
                score_percent=score,
            )
        )
    return summaries


@router.get("/audit/{audit_id}/status", response_model=AuditStatusResponse)
async def get_audit_status(
    audit_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AuditStatusResponse:
    """Status + per-framework results for an audit (owner only)."""
    audit_job = await _load_owned_job(db, audit_id, current_user)
    return await _build_status_response(db, audit_job)


@router.get("/audit/{audit_id}/trend")
async def get_trend(
    audit_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Readiness trend: immutable posture snapshots over time, per framework."""
    audit_job = await _load_owned_job(db, audit_id, current_user)
    res = await db.execute(
        select(ComplianceSnapshot)
        .where(ComplianceSnapshot.audit_job_id == audit_job.id)
        .order_by(ComplianceSnapshot.created_at.asc())
    )
    series: dict[str, list[dict]] = {}
    for snap in res.scalars().all():
        series.setdefault(snap.framework, []).append(
            {
                "score_percent": snap.score_percent,
                "pass_count": snap.pass_count,
                "fail_count": snap.fail_count,
                "partial_count": snap.partial_count,
                "score_delta": snap.score_delta,
                "at": snap.created_at.isoformat() if snap.created_at else None,
            }
        )
    return {"audit_id": audit_id, "trend": series}


@router.get("/audit/{audit_id}/remediation")
async def get_remediation(
    audit_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Return all non-passing controls with gaps + remediation guidance."""
    audit_job = await _load_owned_job(db, audit_id, current_user)
    res = await db.execute(
        select(AuditResult).where(
            AuditResult.audit_job_id == audit_job.id, AuditResult.status != "PASS"
        )
    )
    items = []
    for r in res.scalars().all():
        s = r.raw_evidence_summary or {}
        items.append(
            {
                "framework": r.framework,
                "control_id": r.control_id,
                "control_name": r.control_name,
                "status": r.status,
                "gaps": s.get("gaps", []),
                "remediation": s.get("remediation", ""),
                "category": s.get("category", ""),
            }
        )
    return {"audit_id": audit_id, "items": items, "total": len(items)}


# ═══════════════════════════════════════════════════════════════════════════════
# Exports: PDF / CSV / evidence ZIP
# ═══════════════════════════════════════════════════════════════════════════════


async def _serve_report(db, audit_job, framework_id: str):
    res = await db.execute(
        select(AuditResult).where(
            AuditResult.audit_job_id == audit_job.id, AuditResult.framework == framework_id
        )
    )
    rows = list(res.scalars().all())
    if not rows:
        raise HTTPException(status_code=404, detail=f"No results for framework {framework_id}")
    storage = create_storage_backend()
    cached_key = (audit_job.report_keys or {}).get(framework_id)
    if cached_key:
        pdf_path = await storage.get_file_path(cached_key)
    else:
        loop = asyncio.get_event_loop()
        framework = get_framework(framework_id)
        pdf_local = await loop.run_in_executor(
            None, generate_compliance_report, audit_job, rows, framework.name, framework_id
        )
        pdf_bytes = Path(pdf_local).read_bytes()
        storage_key = f"compliance_reports/{audit_job.id}/{framework_id}.pdf"
        await storage.save_file_from_bytes(storage_key, pdf_bytes)
        report_keys = dict(audit_job.report_keys or {})
        report_keys[framework_id] = storage_key
        audit_job.report_keys = report_keys
        if not audit_job.pdf_storage_key:
            audit_job.pdf_storage_key = storage_key
        await db.commit()
        pdf_path = await storage.get_file_path(storage_key)

    company_slug = audit_job.company_name.lower().replace(" ", "_")
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{company_slug}_{framework_id}_evidence_{date_str}.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/audit/{audit_id}/report")
async def download_audit_report(
    audit_id: str,
    framework: str | None = Query(default=None),
    format: str = Query(default="pdf"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a per-framework report as PDF (default) or CSV."""
    audit_job = await _load_owned_job(db, audit_id, current_user)
    if audit_job.status != "complete":
        raise HTTPException(status_code=400, detail="Audit not complete yet. Check /status for progress.")

    framework_id = framework or (audit_job.frameworks or [DEFAULT_FRAMEWORK])[0]
    if not is_registered(framework_id):
        raise HTTPException(status_code=404, detail="Unknown framework")

    if format == "csv":
        res = await db.execute(
            select(AuditResult).where(
                AuditResult.audit_job_id == audit_job.id, AuditResult.framework == framework_id
            )
        )
        rows = list(res.scalars().all())
        if not rows:
            raise HTTPException(status_code=404, detail=f"No results for framework {framework_id}")
        company_slug = audit_job.company_name.lower().replace(" ", "_")
        filename = f"{company_slug}_{framework_id}_results.csv"
        return Response(
            content=_results_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    try:
        return await _serve_report(db, audit_job, framework_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Error serving report: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating report. Check server logs.")


@router.get("/audit/{audit_id}/evidence")
async def download_evidence_pack(
    audit_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Download an auditor evidence pack ZIP: normalized signals + per-framework CSVs."""
    audit_job = await _load_owned_job(db, audit_id, current_user)
    if audit_job.status != "complete":
        raise HTTPException(status_code=400, detail="Audit not complete yet.")

    res = await db.execute(select(AuditResult).where(AuditResult.audit_job_id == audit_job.id))
    all_rows = list(res.scalars().all())
    grouped = _group_by_framework(all_rows)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "company_name": audit_job.company_name,
            "frameworks": audit_job.frameworks or [DEFAULT_FRAMEWORK],
            "audit_period": f"{audit_job.audit_start_date} to {audit_job.audit_end_date}",
            "generated_at": datetime.utcnow().isoformat(),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("evidence_signals.json", json.dumps(audit_job.evidence_signals or {}, indent=2))
        for framework_id, rows in grouped.items():
            zf.writestr(f"{framework_id}_results.csv", _results_csv(rows))
    buf.seek(0)

    company_slug = audit_job.company_name.lower().replace(" ", "_")
    filename = f"{company_slug}_evidence_pack.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Share links (read-only, scoped, expiring)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/audit/{audit_id}/share", response_model=ShareResponse)
async def create_share_link(
    audit_id: str,
    expires_days: int = Query(default=7, ge=1, le=30),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """Create a scoped, expiring read-only share link for external auditors."""
    audit_job = await _load_owned_job(db, audit_id, current_user)
    token = security.create_audit_share_token(str(audit_job.id), expire_days=expires_days)
    return ShareResponse(token=token, url=f"/api/v1/audit/shared/{token}", expires_days=expires_days)


@router.get("/audit/shared/{token}", response_model=AuditStatusResponse)
async def get_shared_audit(token: str, db: AsyncSession = Depends(get_db)) -> AuditStatusResponse:
    """Read-only shared audit results (no authentication; token-scoped)."""
    audit_id = security.decode_audit_share_token(token)
    try:
        job_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")
    res = await db.execute(select(AuditJob).where(AuditJob.id == job_uuid))
    audit_job = res.scalar_one_or_none()
    if audit_job is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    return await _build_status_response(db, audit_job)

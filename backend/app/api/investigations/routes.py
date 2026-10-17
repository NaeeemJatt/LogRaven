# LogRaven — Investigation Routes

import asyncio
import uuid
from math import ceil
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.cloud.consent import cloud_ai_enabled, require_cloud_ai_consent
from app.config import settings
from app.dependencies import ensure_pro_or_team_tier, get_current_user, get_db, get_storage
from app.limiter import limiter
from app.models.investigation import Investigation
from app.models.investigation_file import InvestigationFile
from app.schemas.investigation import (
    InvestigationAnalyzeRequest,
    InvestigationCreate,
    InvestigationFileResponse,
    InvestigationResponse,
    InvestigationStatusResponse,
    InvestigationUpdate,
)
from app.api.reports.helpers import build_report_response
from app.models.finding import Finding
from app.models.report import Report
from app.services import report_service
from app.utils.audit import add_audit as _add_audit
from app.utils.logger import get_logger
from app.utils.storage import StorageBackend

logger = get_logger(__name__)

router = APIRouter()
findings_router = APIRouter()

# ponytail: offset pagination is adequate for per-user datasets; move to cursors
# only after measured accounts make deep offsets a real bottleneck.
_DISPATCH_FAILURE_MESSAGE = (
    "Analysis could not be dispatched to a worker due to an internal error. "
    "Please retry."
)

# Strong references to in-flight background pipeline tasks. asyncio.create_task
# only creates a weak reference from the event loop, so without keeping our own
# reference the task can be garbage-collected mid-run — silently cancelling the
# pipeline and stranding the investigation at "queued". Holding the reference
# until the task finishes removes that internal failure mode.
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _spawn_pipeline_task(coro, *, name: str) -> None:
    task = asyncio.create_task(coro, name=name)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


def _ensure_pro_for_multi_source_correlation(inv: Investigation, user) -> None:
    """Cross-source correlation (2+ distinct source_type) requires pro or team."""
    if not inv.correlation_enabled:
        return
    if len({f.source_type for f in inv.files}) < 2:
        return
    ensure_pro_or_team_tier(
        user,
        detail="Cross-source correlation requires the pro or team plan.",
    )


def _analyze_claim_statement(
    investigation_id: uuid.UUID,
    user_id: uuid.UUID,
    queued_at: datetime,
):
    """Atomically claim a draft/failed investigation for one analysis request."""
    return (
        update(Investigation)
        .where(
            Investigation.id == investigation_id,
            Investigation.user_id == user_id,
            Investigation.status.in_(["draft", "failed"]),
        )
        .values(
            status="queued",
            progress_stage="queued",
            queued_at=queued_at,
            completed_at=None,
            error_message=None,
        )
        .execution_options(synchronize_session=False)
    )


def _dispatch_failure_compensation_statement(
    investigation_id: uuid.UUID,
    user_id: uuid.UUID,
):
    """Fail only the still-queued row owned by this request's user."""
    return (
        update(Investigation)
        .where(
            Investigation.id == investigation_id,
            Investigation.user_id == user_id,
            Investigation.status == "queued",
        )
        .values(
            status="failed",
            progress_stage="queued",
            completed_at=None,
            error_message=_DISPATCH_FAILURE_MESSAGE,
        )
        .execution_options(synchronize_session=False)
    )


def _effective_progress_stage(status: str) -> str:
    """Fallback when progress_stage column is unset (legacy rows)."""
    if status == "queued":
        return "queued"
    if status == "processing":
        return "parsing"
    if status == "complete":
        return "complete"
    if status == "failed":
        # Must match frontend STAGE_INDEX keys — never return a bare "failed" stage
        return "queued"
    return "queued"


def _serialize_investigation_response(inv: Investigation) -> InvestigationResponse:
    payload = InvestigationResponse.model_validate(inv)
    # Findings roll-up comes from the already-computed report.severity_counts
    # (e.g. {"critical": 2, "high": 1, "informational": 5}). Requires the
    # report relationship to be eager-loaded by the caller.
    severity_summary: dict[str, int] = {}
    findings_count = 0
    report = inv.report
    if report is not None and report.severity_counts:
        severity_summary = {
            str(k): int(v)
            for k, v in report.severity_counts.items()
            if isinstance(v, (int, float))
        }
        findings_count = sum(severity_summary.values())
    return payload.model_copy(update={
        "cloud_ai_enabled": cloud_ai_enabled(),
        "findings_count": findings_count,
        "severity_summary": severity_summary,
    })


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_investigation_or_404(
    investigation_id: uuid.UUID,
    current_user,
    db: AsyncSession,
    *,
    load_files: bool = False,
) -> Investigation:
    q = select(Investigation).where(
        Investigation.id == investigation_id,
        Investigation.user_id == current_user.id,
    )
    if load_files:
        q = q.options(selectinload(Investigation.files), selectinload(Investigation.report))
    result = await db.execute(q)
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


# ── POST /api/v1/investigations ───────────────────────────────────────────────

@router.post("", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
    request: Request,
    body: InvestigationCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    name = body.name.strip()
    if not name or len(name) > 200:
        raise HTTPException(status_code=400, detail="name must be 1-200 characters")

    inv = Investigation(
        user_id=current_user.id,
        name=name,
    )
    db.add(inv)
    await db.flush()
    _add_audit(db, user_id=current_user.id, action="investigation_created", request=request, metadata={
        "investigation_id": str(inv.id),
        "name": name,
    })
    await db.commit()
    await db.refresh(inv)

    # Re-fetch with files relationship (empty list at creation)
    result = await db.execute(
        select(Investigation)
        .options(selectinload(Investigation.files), selectinload(Investigation.report))
        .where(Investigation.id == inv.id)
    )
    return _serialize_investigation_response(result.scalar_one())


# ── GET /api/v1/investigations ────────────────────────────────────────────────

@router.get("", response_model=list[InvestigationResponse])
async def list_investigations(
    response: Response,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    sort: Literal["name", "status", "created_at"] = "created_at",
    direction: Literal["asc", "desc"] = "desc",
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(1, limit), 100)
    offset = (page - 1) * limit
    filters = [Investigation.user_id == current_user.id]
    normalized_search = (search or "").strip()
    if normalized_search:
        filters.append(Investigation.name.ilike(f"%{normalized_search}%"))

    total = (
        await db.execute(select(func.count(Investigation.id)).where(*filters))
    ).scalar_one() or 0

    sort_column = {
        "name": Investigation.name,
        "status": Investigation.status,
        "created_at": Investigation.created_at,
    }[sort]
    order = sort_column.asc() if direction == "asc" else sort_column.desc()
    stable_order = Investigation.id.asc() if direction == "asc" else Investigation.id.desc()
    result = await db.execute(
        select(Investigation)
        .options(selectinload(Investigation.files), selectinload(Investigation.report))
        .where(*filters)
        .order_by(order, stable_order)
        .offset(offset)
        .limit(limit)
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(ceil(total / limit) if total else 0)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(limit)
    return [_serialize_investigation_response(inv) for inv in result.scalars().all()]


# ── GET /api/v1/findings ─────────────────────────────────────────────────────

@findings_router.get("")
async def list_findings(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    severity: Literal["critical", "high", "medium", "low", "informational"] | None = None,
    search: str | None = Query(default=None, max_length=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return safe finding summaries from reports owned by the authenticated user."""
    limit = min(max(1, limit), 100)
    normalized_search = (search or "").strip()
    owner_filters = [
        Report.user_id == current_user.id,
        Investigation.user_id == current_user.id,
    ]
    search_filter = None
    if normalized_search:
        term = f"%{normalized_search}%"
        search_filter = or_(
            Finding.title.ilike(term),
            Finding.description.ilike(term),
            Finding.mitre_technique_id.ilike(term),
            Investigation.name.ilike(term),
        )

    filtered = [*owner_filters]
    if search_filter is not None:
        filtered.append(search_filter)
    if severity:
        filtered.append(Finding.severity == severity)

    joined_count = (
        select(func.count(Finding.id))
        .join(Report, Finding.report_id == Report.id)
        .join(Investigation, Report.investigation_id == Investigation.id)
        .where(*filtered)
    )
    total = (await db.execute(joined_count)).scalar_one() or 0

    count_filters = [*owner_filters]
    if search_filter is not None:
        count_filters.append(search_filter)
    severity_rows = await db.execute(
        select(Finding.severity, func.count(Finding.id))
        .join(Report, Finding.report_id == Report.id)
        .join(Investigation, Report.investigation_id == Investigation.id)
        .where(*count_filters)
        .group_by(Finding.severity)
    )
    severity_counts = {str(level): int(count) for level, count in severity_rows.all()}

    rows = await db.execute(
        select(
            Finding,
            Report.id,
            Investigation.id,
            Investigation.name,
            Investigation.created_at,
        )
        .join(Report, Finding.report_id == Report.id)
        .join(Investigation, Report.investigation_id == Investigation.id)
        .where(*filtered)
        .order_by(Finding.created_at.desc(), Finding.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )

    items = []
    for finding, report_id, investigation_id, investigation_name, investigation_created_at in rows.all():
        items.append({
            "id": str(finding.id),
            "report_id": str(report_id),
            "severity": finding.severity,
            "title": finding.title,
            "description": finding.description,
            "finding_type": finding.finding_type,
            "mitre_technique_id": finding.mitre_technique_id,
            "mitre_technique_name": finding.mitre_technique_name,
            "mitre_tactic": finding.mitre_tactic,
            "remediation": finding.remediation,
            "source_files": finding.source_files or [],
            "confidence": finding.confidence,
            "created_at": finding.created_at.isoformat() if finding.created_at else None,
            "investigation": {
                "id": str(investigation_id),
                "name": investigation_name,
                "created_at": (
                    investigation_created_at.isoformat()
                    if investigation_created_at
                    else None
                ),
            },
        })

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": ceil(total / limit) if total else 0,
        "severity_counts": severity_counts,
    }


# ── GET /api/v1/investigations/{id} ──────────────────────────────────────────

@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)
    return _serialize_investigation_response(inv)


# ── PATCH /api/v1/investigations/{id} ────────────────────────────────────────

@router.patch("/{investigation_id}", response_model=InvestigationResponse)
async def update_investigation(
    investigation_id: uuid.UUID,
    body: InvestigationUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)
    if inv.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=400,
            detail="Correlation can only be changed for draft or failed investigations.",
        )

    inv.correlation_enabled = body.correlation_enabled
    await db.commit()
    return _serialize_investigation_response(inv)


# ── DELETE /api/v1/investigations/{id} ────────────────────────────────────────

@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(
    request: Request,
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)

    # Purge blobs (uploaded logs + report PDF) so storage never accumulates
    # orphans. Best-effort: a missing blob must not block the delete.
    blob_keys = [f.storage_key for f in inv.files if f.storage_key]
    report_result = await db.execute(
        select(Report.pdf_storage_key).where(Report.investigation_id == inv.id)
    )
    pdf_key = report_result.scalar_one_or_none()
    if pdf_key:
        blob_keys.append(pdf_key)
    for key in blob_keys:
        try:
            await storage.delete_file(key)
        except Exception:
            logger.warning("Blob cleanup failed for %s (continuing delete)", key)

    _add_audit(db, user_id=current_user.id, action="investigation_deleted", request=request, metadata={
        "investigation_id": str(investigation_id),
        "name": inv.name,
        "file_count": len(inv.files),
    })
    await db.delete(inv)
    await db.commit()


# ── POST /api/v1/investigations/{id}/files ────────────────────────────────────

@router.post("/{investigation_id}/files", response_model=InvestigationFileResponse, status_code=201)
@limiter.limit("120/hour")
async def upload_file(
    request: Request,
    investigation_id: uuid.UUID,
    source_type: str = Form(...),
    file: UploadFile = File(...),
    ingestion_mode: str = Form("parsers"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    from app.api.investigations.validators import (
        VALID_SOURCE_TYPES,
        sanitize_upload_filename,
        validate_file_upload,
    )

    inv = await _get_investigation_or_404(investigation_id, current_user, db)
    if inv.status not in ("draft",):
        raise HTTPException(status_code=400, detail="Cannot add files to an investigation that is not in draft status")

    if source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid source_type. Must be one of: {sorted(VALID_SOURCE_TYPES)}")

    im = (ingestion_mode or "parsers").strip().lower()
    if im not in ("parsers", "decoders"):
        raise HTTPException(
            status_code=400,
            detail="Invalid ingestion_mode. Must be 'parsers' or 'decoders'.",
        )

    filename = sanitize_upload_filename(file.filename or "upload")
    await validate_file_upload(file, current_user.tier, logical_filename=filename)
    file_id = uuid.uuid4()
    storage_key = f"uploads/{investigation_id}/{file_id}_{filename}"

    await storage.save_file(file, storage_key)

    inv_file = InvestigationFile(
        id=file_id,
        investigation_id=investigation_id,
        filename=filename,
        source_type=source_type,
        ingestion_mode=im,
        storage_key=storage_key,
        status="pending",
    )
    db.add(inv_file)
    _add_audit(db, user_id=current_user.id, action="upload", request=request, metadata={
        "investigation_id": str(investigation_id),
        "file_id": str(file_id),
        "filename": filename,
        "source_type": source_type,
    })
    await db.commit()
    await db.refresh(inv_file)
    return inv_file


# ── DELETE /api/v1/investigations/{id}/files/{file_id} ───────────────────────

@router.delete("/{investigation_id}/files/{file_id}", status_code=204)
async def delete_file(
    request: Request,
    investigation_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db)
    if inv.status != "draft":
        raise HTTPException(status_code=400, detail="Files can only be removed when investigation is in draft status")

    result = await db.execute(
        select(InvestigationFile).where(
            InvestigationFile.id == file_id,
            InvestigationFile.investigation_id == investigation_id,
        )
    )
    inv_file = result.scalar_one_or_none()
    if inv_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    await storage.delete_file(inv_file.storage_key)
    _add_audit(db, user_id=current_user.id, action="file_deleted", request=request, metadata={
        "investigation_id": str(investigation_id),
        "file_id": str(file_id),
        "filename": inv_file.filename,
    })
    await db.delete(inv_file)
    await db.commit()


# ── POST /api/v1/investigations/{id}/analyze ─────────────────────────────────

@router.post("/{investigation_id}/analyze")
@limiter.limit("60/hour")
async def analyze_investigation(
    request: Request,
    investigation_id: uuid.UUID,
    body: InvestigationAnalyzeRequest = Body(default_factory=InvestigationAnalyzeRequest),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)

    if not inv.files:
        raise HTTPException(status_code=400, detail="Upload at least one file first")

    if inv.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot analyze investigation with status '{inv.status}'. Must be draft or failed.",
        )

    _ensure_pro_for_multi_source_correlation(inv, current_user)
    require_cloud_ai_consent(body.cloud_ai_consent)

    from app.utils.rate_limiter import (
        check_and_count_analysis,
        refund_analysis_quota,
    )

    queued_at = datetime.utcnow()
    claim = await db.execute(
        _analyze_claim_statement(investigation_id, current_user.id, queued_at)
    )
    if claim.rowcount != 1:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze investigation because it has already been started.",
        )

    try:
        allowed, _remaining = await check_and_count_analysis(
            str(current_user.id),
            current_user.tier,
        )
    except Exception:
        await db.rollback()
        raise
    if not allowed:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Daily analysis limit reached for your plan. "
                "Try again tomorrow or contact your administrator about plan limits."
            ),
        )
    quota_counted = _remaining >= 0

    inv.status = "queued"
    inv.progress_stage = "queued"
    inv.queued_at = queued_at
    inv.completed_at = None
    inv.error_message = None
    _add_audit(db, user_id=current_user.id, action="analyze", request=request, metadata={
        "investigation_id": str(investigation_id),
        "file_count": len(inv.files),
        "cloud_ai_consent": bool(body.cloud_ai_consent),
    })
    await db.commit()

    inv_id_str = str(investigation_id)
    consent = body.cloud_ai_consent

    if settings.USE_ASYNCIO_INVESTIGATION_PIPELINE:
        from app.tasks.process_investigation import run_investigation_pipeline_inline

        _spawn_pipeline_task(
            run_investigation_pipeline_inline(inv_id_str, cloud_ai_consent=consent),
            name=f"lograven-pipeline-{inv_id_str[:8]}",
        )
    else:
        from app.tasks.dev_worker import ensure_dev_worker_running
        from app.tasks.process_investigation import process_investigation

        try:
            if not ensure_dev_worker_running():
                raise RuntimeError("Celery worker is unavailable")
            process_investigation.delay(inv_id_str, consent)
        except Exception as dispatch_exc:
            logger.exception(
                "Failed to dispatch investigation %s to Celery",
                investigation_id,
            )
            compensated = False
            try:
                compensation = await db.execute(
                    _dispatch_failure_compensation_statement(
                        investigation_id,
                        current_user.id,
                    )
                )
                compensated = compensation.rowcount == 1
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception(
                    "Failed to compensate queued investigation %s",
                    investigation_id,
                )

            if compensated:
                inv.status = "failed"
                inv.progress_stage = "queued"
                inv.completed_at = None
                inv.error_message = _DISPATCH_FAILURE_MESSAGE
                if quota_counted:
                    try:
                        await refund_analysis_quota(
                            str(current_user.id),
                            current_user.tier,
                        )
                    except Exception:
                        logger.exception(
                            "Unexpected quota refund failure for investigation %s",
                            investigation_id,
                        )

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_DISPATCH_FAILURE_MESSAGE,
            ) from dispatch_exc

    return {"status": "queued", "investigation_id": inv_id_str}


# ── GET /api/v1/investigations/{id}/status ───────────────────────────────────

@router.get("/{investigation_id}/status", response_model=InvestigationStatusResponse)
async def get_investigation_status(
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)
    effective_stage = inv.progress_stage or _effective_progress_stage(inv.status)
    return InvestigationStatusResponse(
        id=inv.id,
        status=inv.status,
        progress_stage=effective_stage,
        error_message=inv.error_message,
        queued_at=inv.queued_at,
        files=[InvestigationFileResponse.model_validate(f) for f in inv.files],
    )


# ── GET /api/v1/investigations/{id}/report ────────────────────────────────────

@router.get("/{investigation_id}/report")
async def get_report(
    request: Request,
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_investigation_or_404(investigation_id, current_user, db)
    report, findings = await report_service.get_report_by_investigation(
        investigation_id, current_user.id, db
    )
    _add_audit(db, user_id=current_user.id, action="report_view", request=request, metadata={
        "investigation_id": str(investigation_id),
        "report_id": str(report.id),
    })
    await db.commit()
    return build_report_response(report, findings)


# ── GET /api/v1/investigations/{id}/report/download ──────────────────────────

@router.get("/{investigation_id}/report/download")
async def download_report_pdf(
    request: Request,
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    await _get_investigation_or_404(investigation_id, current_user, db)
    report = await report_service.get_report_row_for_investigation(
        investigation_id, current_user.id, db
    )
    payload = report_service.pdf_download_payload(report, storage)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="PDF not generated yet. Try again or re-run analysis.",
        )
    _add_audit(db, user_id=current_user.id, action="download", request=request, metadata={
        "investigation_id": str(investigation_id),
        "kind": "report_pdf",
    })
    await db.commit()
    return payload

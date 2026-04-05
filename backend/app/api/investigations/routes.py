# LogRaven — Investigation Routes

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select, func
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
)
from app.api.reports.helpers import build_report_response
from app.models.finding import Finding
from app.services import report_service
from app.utils.storage import StorageBackend

router = APIRouter()

# Cap OFFSET cost: max page × max limit stays bounded for PostgreSQL
_MAX_INVESTIGATION_LIST_PAGE = 2000


def _ensure_pro_for_multi_source_correlation(inv: Investigation, user) -> None:
    """Cross-source correlation (2+ distinct source_type) requires pro or team."""
    if not inv.correlation_enabled:
        return
    if len({f.source_type for f in inv.files}) < 2:
        return
    ensure_pro_or_team_tier(
        user,
        detail="Cross-source correlation requires a pro or team subscription.",
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
    return payload.model_copy(update={"cloud_ai_enabled": cloud_ai_enabled()})


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
        q = q.options(selectinload(Investigation.files))
    result = await db.execute(q)
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


# ── POST /api/v1/investigations ───────────────────────────────────────────────

@router.post("", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
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
    await db.commit()
    await db.refresh(inv)

    # Re-fetch with files relationship (empty list at creation)
    result = await db.execute(
        select(Investigation)
        .options(selectinload(Investigation.files))
        .where(Investigation.id == inv.id)
    )
    return _serialize_investigation_response(result.scalar_one())


# ── GET /api/v1/investigations ────────────────────────────────────────────────

@router.get("", response_model=list[InvestigationResponse])
async def list_investigations(
    page: int = 1,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = min(max(1, page), _MAX_INVESTIGATION_LIST_PAGE)
    limit = min(max(1, limit), 100)
    offset = (page - 1) * limit
    result = await db.execute(
        select(Investigation)
        .options(selectinload(Investigation.files))
        .where(Investigation.user_id == current_user.id)
        .order_by(Investigation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_serialize_investigation_response(inv) for inv in result.scalars().all()]


# ── GET /api/v1/investigations/{id} ──────────────────────────────────────────

@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)
    return _serialize_investigation_response(inv)


# ── DELETE /api/v1/investigations/{id} ────────────────────────────────────────

@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db)
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
    await db.commit()
    await db.refresh(inv_file)
    return inv_file


# ── DELETE /api/v1/investigations/{id}/files/{file_id} ───────────────────────

@router.delete("/{investigation_id}/files/{file_id}", status_code=204)
async def delete_file(
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

    inv.status = "queued"
    inv.progress_stage = "queued"
    await db.commit()

    inv_id_str = str(investigation_id)
    consent = body.cloud_ai_consent

    if settings.USE_ASYNCIO_INVESTIGATION_PIPELINE:
        from app.tasks.process_investigation import run_investigation_pipeline_inline

        asyncio.create_task(
            run_investigation_pipeline_inline(inv_id_str, cloud_ai_consent=consent),
            name=f"lograven-pipeline-{inv_id_str[:8]}",
        )
    else:
        from app.tasks.dev_worker import ensure_dev_worker_running
        from app.tasks.process_investigation import process_investigation

        ensure_dev_worker_running()
        process_investigation.delay(inv_id_str, consent)

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
        files=[InvestigationFileResponse.model_validate(f) for f in inv.files],
    )


# ── GET /api/v1/investigations/{id}/report ────────────────────────────────────

@router.get("/{investigation_id}/report")
async def get_report(
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_investigation_or_404(investigation_id, current_user, db)
    report, findings = await report_service.get_report_by_investigation(
        investigation_id, current_user.id, db
    )
    return build_report_response(report, findings)


# ── GET /api/v1/investigations/{id}/report/download ──────────────────────────

@router.get("/{investigation_id}/report/download")
async def download_report_pdf(
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
    return payload

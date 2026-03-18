# LogRaven — Investigation Routes

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db, get_storage
from app.models.investigation import Investigation
from app.models.investigation_file import InvestigationFile
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationFileResponse,
    InvestigationResponse,
    InvestigationStatusResponse,
)
from app.utils.storage import StorageBackend

router = APIRouter()


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
    return result.scalar_one()


# ── GET /api/v1/investigations ────────────────────────────────────────────────

@router.get("", response_model=list[InvestigationResponse])
async def list_investigations(
    page: int = 1,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    result = await db.execute(
        select(Investigation)
        .options(selectinload(Investigation.files))
        .where(Investigation.user_id == current_user.id)
        .order_by(Investigation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


# ── GET /api/v1/investigations/{id} ──────────────────────────────────────────

@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)


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
async def upload_file(
    investigation_id: uuid.UUID,
    source_type: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    from app.api.investigations.validators import ALLOWED_EXTENSIONS, TIER_SIZE_LIMITS, VALID_SOURCE_TYPES

    inv = await _get_investigation_or_404(investigation_id, current_user, db)
    if inv.status not in ("draft",):
        raise HTTPException(status_code=400, detail="Cannot add files to an investigation that is not in draft status")

    if source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid source_type. Must be one of: {sorted(VALID_SOURCE_TYPES)}")

    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type .{ext} not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    size_limit = TIER_SIZE_LIMITS.get(current_user.tier, TIER_SIZE_LIMITS["free"])
    file_id = uuid.uuid4()
    storage_key = f"uploads/{investigation_id}/{file_id}_{filename}"

    await storage.save_file(file, storage_key)

    inv_file = InvestigationFile(
        id=file_id,
        investigation_id=investigation_id,
        filename=filename,
        source_type=source_type,
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

    await db.delete(inv_file)
    await db.commit()


# ── POST /api/v1/investigations/{id}/analyze ─────────────────────────────────

@router.post("/{investigation_id}/analyze")
async def analyze_investigation(
    investigation_id: uuid.UUID,
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

    inv.status = "queued"
    await db.commit()

    from app.tasks.process_investigation import process_investigation
    process_investigation.delay(str(investigation_id))

    return {"status": "queued", "investigation_id": str(investigation_id)}


# ── GET /api/v1/investigations/{id}/status ───────────────────────────────────

@router.get("/{investigation_id}/status", response_model=InvestigationStatusResponse)
async def get_investigation_status(
    investigation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_investigation_or_404(investigation_id, current_user, db, load_files=True)
    return InvestigationStatusResponse(
        id=inv.id,
        status=inv.status,
        progress_stage=inv.status,
        files=[
            InvestigationFileResponse(
                id=f.id,
                filename=f.filename,
                source_type=f.source_type,
                log_type=f.log_type,
                status=f.status,
                event_count=f.event_count,
            )
            for f in inv.files
        ],
    )

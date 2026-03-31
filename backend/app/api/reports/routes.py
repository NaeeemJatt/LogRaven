# LogRaven — Report Routes

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_storage
from app.services import report_service
from app.utils.storage import StorageBackend

router = APIRouter()


@router.get("/{report_id}")
async def get_report(
    report_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await report_service.get_report_for_user(
        report_id, current_user.id, db, load_findings=True
    )
    return report_service.report_to_json(report, report.findings)


@router.get("/{report_id}/download")
async def download_report_pdf(
    report_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    report = await report_service.get_report_for_user(report_id, current_user.id, db)
    download = report_service.pdf_download_payload(report, storage)
    if download is None:
        raise HTTPException(
            status_code=404,
            detail="PDF not generated yet. Try again or re-run analysis.",
        )
    return download

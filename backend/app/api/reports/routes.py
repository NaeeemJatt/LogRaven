# LogRaven — Report Routes
#
# ENDPOINTS:
#   GET /api/v1/reports/{report_id}          — full report JSON with all findings
#   GET /api/v1/reports/{report_id}/download — returns URL for PDF download
#
# OWNERSHIP:
#   Both endpoints check report.user_id == current_user.id.
#   A 404 (not 403) is returned on access denial to avoid leaking IDs.

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.reports.helpers import build_download_response, build_report_response
from app.dependencies import get_current_user, get_db, get_storage
from app.models.finding import Finding
from app.models.report import Report
from app.utils.storage import StorageBackend

router = APIRouter()


async def _get_report_or_404(
    report_id: uuid.UUID,
    current_user,
    db: AsyncSession,
    *,
    load_findings: bool = False,
) -> Report:
    """Fetch a report by its own UUID, verifying ownership."""
    q = select(Report).where(
        Report.id == report_id,
        Report.user_id == current_user.id,
    )
    if load_findings:
        q = q.options(selectinload(Report.findings))
    result = await db.execute(q)
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ── GET /api/v1/reports/{report_id} ──────────────────────────────────────────

@router.get("/{report_id}")
async def get_report(
    report_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _get_report_or_404(report_id, current_user, db, load_findings=True)
    return build_report_response(report, report.findings)


# ── GET /api/v1/reports/{report_id}/download ─────────────────────────────────

@router.get("/{report_id}/download")
async def download_report_pdf(
    report_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    report = await _get_report_or_404(report_id, current_user, db)

    download = build_download_response(report, storage)
    if download is None:
        raise HTTPException(
            status_code=404,
            detail="PDF not generated yet. Try again or re-run analysis.",
        )
    return download

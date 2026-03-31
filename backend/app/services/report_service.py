# LogRaven — Report fetch & download helpers

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.reports.helpers import build_download_response, build_report_response
from app.models.report import Report
from app.utils.storage import StorageBackend


async def get_report_for_user(
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    load_findings: bool = False,
) -> Report:
    q = select(Report).where(Report.id == report_id, Report.user_id == user_id)
    if load_findings:
        q = q.options(selectinload(Report.findings))
    result = await db.execute(q)
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def report_to_json(report: Report, findings: list) -> dict:
    return build_report_response(report, findings)


def pdf_download_payload(report: Report, storage: StorageBackend) -> dict | None:
    return build_download_response(report, storage)


async def get_report_by_investigation(
    investigation_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[Report, list]:
    """Return (report, findings) or raise 404."""
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.findings))
        .where(Report.investigation_id == investigation_id, Report.user_id == user_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not ready yet. Run /analyze first.")
    findings = list(report.findings)
    return report, findings


async def get_report_row_for_investigation(
    investigation_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Report:
    """Single Report row by investigation (no findings load) — for PDF download."""
    result = await db.execute(
        select(Report).where(
            Report.investigation_id == investigation_id,
            Report.user_id == user_id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not ready yet. Run /analyze first.")
    return report

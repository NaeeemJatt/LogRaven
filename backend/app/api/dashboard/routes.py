# LogRaven — Dashboard Routes
#
# Provides aggregate stats for the Dashboard page.
# All queries are scoped to the authenticated user.

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.investigation import Investigation
from app.models.investigation_file import InvestigationFile
from app.models.report import Report

router = APIRouter()


class DashboardStatsResponse(BaseModel):
    total_investigations: int
    # Investigations currently queued or processing (not a threat count).
    active_investigations: int
    files_analyzed: int
    avg_analysis_time: str
    status_counts: dict[str, int]
    severity_counts: dict[str, int]
    recent_investigation_dates: list[str]
    recent_daily_counts: dict[str, int]


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregate counts for the authenticated user's dashboard."""
    uid = current_user.id

    # Total investigations
    total_result = await db.execute(
        select(func.count(Investigation.id)).where(Investigation.user_id == uid)
    )
    total = total_result.scalar_one() or 0

    status_result = await db.execute(
        select(Investigation.status, func.count(Investigation.id))
        .where(Investigation.user_id == uid)
        .group_by(Investigation.status)
    )
    status_counts = {str(state): int(count) for state, count in status_result.all()}
    active = status_counts.get("queued", 0) + status_counts.get("processing", 0)

    files_result = await db.execute(
        select(func.count(InvestigationFile.id))
        .join(Investigation, InvestigationFile.investigation_id == Investigation.id)
        .where(
            Investigation.user_id == uid,
            Investigation.status == "complete",
            InvestigationFile.status == "parsed",
        )
    )
    files_analyzed = files_result.scalar_one() or 0

    # Average analysis time: only for complete investigations that have completed_at
    avg_result = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Investigation.completed_at - Investigation.queued_at,
                )
            )
        ).where(
            Investigation.user_id == uid,
            Investigation.status == "complete",
            Investigation.completed_at.is_not(None),
            Investigation.queued_at.is_not(None),
        )
    )
    avg_seconds = avg_result.scalar_one()

    if avg_seconds is None:
        avg_time_str = "—"
    elif avg_seconds < 60:
        avg_time_str = f"{int(avg_seconds)}s"
    elif avg_seconds < 3600:
        avg_time_str = f"{int(avg_seconds // 60)}m"
    else:
        avg_time_str = f"{avg_seconds / 3600:.1f}h"

    severity_result = await db.execute(
        select(Report.severity_counts).where(Report.user_id == uid)
    )
    severity_counts: dict[str, int] = {}
    for counts in severity_result.scalars().all():
        for level, count in (counts or {}).items():
            if isinstance(count, (int, float)):
                severity_counts[str(level)] = severity_counts.get(str(level), 0) + int(count)

    recent_result = await db.execute(
        select(Investigation.created_at).where(
            Investigation.user_id == uid,
            Investigation.created_at
            >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=8),
        ).order_by(Investigation.created_at.desc()).limit(10_000)
    )
    recent_values = [value for value in recent_result.scalars().all() if value is not None]
    recent_dates = [value.isoformat() for value in recent_values[:1000]]
    try:
        user_zone = ZoneInfo(getattr(current_user, "timezone", None) or "UTC")
    except ZoneInfoNotFoundError:
        user_zone = ZoneInfo("UTC")
    recent_daily_counts: dict[str, int] = {}
    for created_at in recent_values:
        local_day = created_at.replace(tzinfo=timezone.utc).astimezone(user_zone).date().isoformat()
        recent_daily_counts[local_day] = recent_daily_counts.get(local_day, 0) + 1

    return DashboardStatsResponse(
        total_investigations=total,
        active_investigations=active,
        files_analyzed=files_analyzed,
        avg_analysis_time=avg_time_str,
        status_counts=status_counts,
        severity_counts=severity_counts,
        recent_investigation_dates=recent_dates,
        recent_daily_counts=recent_daily_counts,
    )

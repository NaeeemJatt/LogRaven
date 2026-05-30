# LogRaven — Dashboard Routes
#
# Provides aggregate stats for the Dashboard page.
# All queries are scoped to the authenticated user.

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.investigation import Investigation

router = APIRouter()


class DashboardStatsResponse(BaseModel):
    total_investigations: int
    active_threats: int
    files_analyzed: int
    avg_analysis_time: str


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

    # Active: queued or processing
    active_result = await db.execute(
        select(func.count(Investigation.id)).where(
            Investigation.user_id == uid,
            Investigation.status.in_(["queued", "processing"]),
        )
    )
    active = active_result.scalar_one() or 0

    # Files analyzed: sum of file counts for complete investigations
    # Use subquery via Investigation.files relationship count
    from app.models.investigation_file import InvestigationFile

    files_result = await db.execute(
        select(func.count(InvestigationFile.id))
        .join(Investigation, InvestigationFile.investigation_id == Investigation.id)
        .where(Investigation.user_id == uid)
    )
    files_analyzed = files_result.scalar_one() or 0

    # Average analysis time: only for complete investigations that have completed_at
    avg_result = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Investigation.completed_at - Investigation.created_at,
                )
            )
        ).where(
            Investigation.user_id == uid,
            Investigation.status == "complete",
            Investigation.completed_at.is_not(None),
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

    return DashboardStatsResponse(
        total_investigations=total,
        active_threats=active,
        files_analyzed=files_analyzed,
        avg_analysis_time=avg_time_str,
    )

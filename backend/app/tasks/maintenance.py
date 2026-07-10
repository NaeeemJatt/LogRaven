# LogRaven — Maintenance tasks (Celery beat)
#
# reconcile_stuck_jobs: a worker crash mid-pipeline leaves investigations at
# 'queued'/'processing' and audit jobs at 'pending'/'running' forever (acks_late
# re-delivers once, but a poison message or OOM-kill loop can still strand rows).
# This sweep fails anything running longer than the task hard time limit so the
# UI unsticks and users can retry.

import asyncio
from datetime import datetime, timedelta

from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Anything "running" longer than this is considered dead (> task_time_limit + slack).
STUCK_AFTER = timedelta(hours=1)

_INVESTIGATION_MESSAGE = (
    "Analysis was interrupted unexpectedly and did not finish. "
    "Click Analyze to run it again."
)
_AUDIT_MESSAGE = (
    "The audit was interrupted unexpectedly and did not finish. "
    "Start a new audit to try again."
)


@celery_app.task(name="maintenance.reconcile_stuck_jobs")
def reconcile_stuck_jobs() -> dict:
    return asyncio.run(_reconcile())


async def _reconcile() -> dict:
    from sqlalchemy import update
    from app.dependencies import AsyncSessionLocal
    from app.models.investigation import Investigation
    from app.models.soc2_audit import AuditJob

    # Columns are TIMESTAMP WITHOUT TIME ZONE holding UTC values — compare naive UTC.
    cutoff = datetime.utcnow() - STUCK_AFTER

    async with AsyncSessionLocal() as db:
        inv_result = await db.execute(
            update(Investigation)
            .where(
                Investigation.status.in_(["queued", "processing"]),
                Investigation.created_at < cutoff,
            )
            .values(status="failed", error_message=_INVESTIGATION_MESSAGE)
        )
        audit_result = await db.execute(
            update(AuditJob)
            .where(
                AuditJob.status.in_(["pending", "running"]),
                AuditJob.updated_at < cutoff,
            )
            .values(status="failed", error_message=_AUDIT_MESSAGE)
        )
        await db.commit()

    investigations = inv_result.rowcount or 0
    audits = audit_result.rowcount or 0
    if investigations or audits:
        logger.warning(
            "[reconcile] failed stuck jobs | investigations=%d | audits=%d",
            investigations, audits,
        )
    return {"investigations": investigations, "audits": audits}

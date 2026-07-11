# LogRaven — Maintenance tasks (Celery beat)
#
# reconcile_stuck_jobs: a worker crash mid-pipeline leaves investigations at
# 'queued'/'processing' and audit jobs at 'pending'/'running' forever (acks_late
# re-delivers once, but a poison message or OOM-kill loop can still strand rows).
# This sweep fails anything running longer than the task hard time limit so the
# UI unsticks and users can retry.
#
# purge_expired_audit_logs: enforces the 1-year audit-trail retention policy
# documented in models/audit.py by deleting rows older than the cutoff.

from datetime import datetime, timedelta

from app.tasks.async_runner import run_async
from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Anything "running" longer than this is considered dead (> task_time_limit + slack).
STUCK_AFTER = timedelta(hours=1)

# Audit-trail retention (models/audit.py documents a 1-year policy).
AUDIT_LOG_RETENTION = timedelta(days=365)

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
    return run_async(_reconcile())


def _stuck_investigations_update(cutoff: datetime):
    from sqlalchemy import update
    from app.models.investigation import Investigation

    return (
        update(Investigation)
        .where(
            Investigation.status.in_(["queued", "processing"]),
            Investigation.queued_at < cutoff,
        )
        .values(status="failed", error_message=_INVESTIGATION_MESSAGE)
    )


async def _reconcile() -> dict:
    from sqlalchemy import update
    from app.dependencies import AsyncSessionLocal
    from app.models.soc2_audit import AuditJob

    # Columns are TIMESTAMP WITHOUT TIME ZONE holding UTC values — compare naive UTC.
    cutoff = datetime.utcnow() - STUCK_AFTER

    async with AsyncSessionLocal() as db:
        inv_result = await db.execute(
            _stuck_investigations_update(cutoff)
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


@celery_app.task(name="maintenance.purge_expired_reports")
def purge_expired_reports() -> dict:
    return run_async(_purge_reports())


async def _purge_reports() -> dict:
    """
    Per-tier report retention (REPORT_RETENTION_DAYS_FREE/PRO/TEAM; 0 = keep
    forever). Deletes expired Report rows via the ORM so findings cascade, and
    removes the cached PDF blob best-effort.
    """
    from sqlalchemy import select
    from app.config import settings
    from app.dependencies import AsyncSessionLocal
    from app.models.report import Report
    from app.models.user import User
    from app.utils.storage import create_storage_backend

    retention = {
        "free": settings.REPORT_RETENTION_DAYS_FREE,
        "pro":  settings.REPORT_RETENTION_DAYS_PRO,
        "team": settings.REPORT_RETENTION_DAYS_TEAM,
    }
    if all(days <= 0 for days in retention.values()):
        return {"purged": 0}

    storage = create_storage_backend()
    purged = 0
    async with AsyncSessionLocal() as db:
        for tier, days in retention.items():
            if days <= 0:
                continue
            cutoff = datetime.utcnow() - timedelta(days=days)
            res = await db.execute(
                select(Report)
                .join(User, Report.user_id == User.id)
                .where(User.tier == tier, Report.created_at < cutoff)
            )
            for report in res.scalars().all():
                if report.pdf_storage_key:
                    try:
                        await storage.delete_file(report.pdf_storage_key)
                    except Exception:  # noqa: BLE001 — blob may already be gone
                        pass
                await db.delete(report)
                purged += 1
        await db.commit()

    if purged:
        logger.info("[retention] purged %d expired report(s)", purged)
    return {"purged": purged}


@celery_app.task(name="maintenance.purge_expired_audit_logs")
def purge_expired_audit_logs() -> dict:
    return run_async(_purge_audit_logs())


async def _purge_audit_logs() -> dict:
    from sqlalchemy import delete
    from app.dependencies import AsyncSessionLocal
    from app.models.audit import AuditLog

    cutoff = datetime.utcnow() - AUDIT_LOG_RETENTION
    async with AsyncSessionLocal() as db:
        result = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await db.commit()

    purged = result.rowcount or 0
    if purged:
        logger.info("[retention] purged %d audit-log rows older than %s", purged, cutoff.date())
    return {"purged": purged}

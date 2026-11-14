"""Background zombie reaper and sweeper tasks for LogRaven state machines."""

from datetime import datetime, timedelta
from sqlalchemy import select, or_
from app.models.investigation import Investigation
from app.models.soc2_audit import AuditJob, ComplianceException
from app.schemas.enums import InvestigationStatus, AuditJobStatus, ExceptionStatus
from app.utils.logger import get_logger

logger = get_logger("lograven.reaper")


async def sweep_stale_investigations(
    db,
    timeout_minutes: int = 15,
) -> list[str]:
    """Sweeps investigations stuck in 'processing' past timeout_minutes without a heartbeat."""
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    query = select(Investigation).where(
        Investigation.status == InvestigationStatus.PROCESSING,
        or_(
            Investigation.heartbeat_at < cutoff,
            (Investigation.heartbeat_at.is_(None) & (Investigation.queued_at < cutoff)),
        ),
    )
    result = await db.execute(query)
    stale_items = list(result.scalars().all())

    reaped_ids = []
    for inv in stale_items:
        logger.warning(
            "Reaping zombie investigation %s stuck in processing (last heartbeat: %s)",
            inv.id,
            inv.heartbeat_at or inv.queued_at,
        )
        inv.transition_to(InvestigationStatus.FAILED)
        inv.error_message = (
            f"Worker timeout: investigation exceeded maximum execution duration ({timeout_minutes}m)"
        )
        inv.completed_at = datetime.utcnow()
        reaped_ids.append(str(inv.id))

    if stale_items:
        await db.commit()
    return reaped_ids


async def sweep_stale_audit_jobs(
    db,
    timeout_minutes: int = 30,
) -> list[str]:
    """Sweeps compliance audit jobs stuck in 'running' past timeout_minutes without a heartbeat."""
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    query = select(AuditJob).where(
        AuditJob.status == AuditJobStatus.RUNNING,
        or_(
            AuditJob.heartbeat_at < cutoff,
            (AuditJob.heartbeat_at.is_(None) & (AuditJob.created_at < cutoff)),
        ),
    )
    result = await db.execute(query)
    stale_jobs = list(result.scalars().all())

    reaped_ids = []
    for job in stale_jobs:
        logger.warning(
            "Reaping zombie audit job %s stuck in running (last heartbeat: %s)",
            job.id,
            job.heartbeat_at or job.created_at,
        )
        job.transition_to(AuditJobStatus.FAILED)
        job.error_message = (
            f"Worker timeout: audit execution exceeded maximum threshold ({timeout_minutes}m)"
        )
        reaped_ids.append(str(job.id))

    if stale_jobs:
        await db.commit()
    return reaped_ids


async def sweep_expired_compliance_exceptions(db) -> list[str]:
    """Sweeps compliance exceptions whose expiration date has passed."""
    now = datetime.utcnow()
    query = select(ComplianceException).where(
        ComplianceException.status == ExceptionStatus.ACTIVE,
        ComplianceException.expires_at.is_not(None),
        ComplianceException.expires_at <= now,
    )
    result = await db.execute(query)
    expired_exceptions = list(result.scalars().all())

    expired_ids = []
    for exc in expired_exceptions:
        exc.transition_to(ExceptionStatus.EXPIRED)
        expired_ids.append(str(exc.id))

    if expired_exceptions:
        await db.commit()
    return expired_ids


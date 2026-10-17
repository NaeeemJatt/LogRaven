"""Autonomous Compliance Scan Scheduler for Cloud Accounts."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soc2_audit import AuditJob, CloudAccount
from app.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_next_run(schedule: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if schedule == "daily":
        return now + timedelta(days=1)
    elif schedule == "weekly":
        return now + timedelta(days=7)
    elif schedule == "monthly":
        return now + timedelta(days=30)
    return None


async def scan_due_cloud_accounts(db: AsyncSession) -> list[str]:
    """Find all cloud accounts due for a scheduled compliance audit and dispatch them."""
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(CloudAccount).where(
            CloudAccount.scan_schedule != "none",
            CloudAccount.next_run_at <= now,
            CloudAccount.health_status != "permission_error",
        )
    )
    due_accounts = list(res.scalars().all())
    if not due_accounts:
        logger.debug("No cloud accounts due for scheduled scan.")
        return []

    logger.info("Found %d cloud accounts due for scheduled scan", len(due_accounts))
    started_ids: list[str] = []

    for account in due_accounts:
        today = date.today()
        start_date = today - timedelta(days=90)

        job = AuditJob(
            user_id=account.user_id,
            cloud_account_id=account.id,
            company_name=account.name,
            role_arn=account.role_arn,
            audit_start_date=start_date,
            audit_end_date=today,
            frameworks=account.default_frameworks or ["soc2"],
            recurrence=account.scan_schedule,
            status="pending",
        )
        db.add(job)
        await db.flush()

        # Advance schedule to the next period
        account.next_run_at = calculate_next_run(account.scan_schedule)
        account.last_scanned_at = now
        started_ids.append(str(job.id))

        logger.info("Enqueued scheduled audit %s for cloud account '%s' (next run: %s)", job.id, account.name, account.next_run_at)

    await db.commit()

    # Dispatch audit execution for all started jobs
    for audit_id in started_ids:
        try:
            from app.config import settings
            from app.tasks.dev_worker import ensure_dev_worker_running

            if settings.USE_ASYNCIO_INVESTIGATION_PIPELINE and not ensure_dev_worker_running():
                from app.compliance.tasks import run_compliance_audit_inline
                asyncio.create_task(run_compliance_audit_inline(audit_id))
            else:
                if ensure_dev_worker_running():
                    from app.compliance.tasks import run_soc2_audit
                    run_soc2_audit.apply_async(args=[audit_id], task_id=audit_id)
        except Exception as exc:
            logger.error("Failed to dispatch scheduled audit %s: %s", audit_id, exc)

    return started_ids

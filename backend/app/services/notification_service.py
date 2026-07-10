# LogRaven — Job completion / failure notifications
#
# Logs a structured line and, when SMTP is configured, emails the user.
# Callers are inside the async pipeline, so email sends are scheduled as
# fire-and-forget tasks; a mail outage can never fail an investigation.

import asyncio

from app.services import email_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _fire_and_forget(coro) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running loop (sync caller) — send inline.
        asyncio.run(coro)


def send_job_complete(
    user_email: str,
    investigation_name: str,
    report_id: str,
    finding_count: int,
) -> None:
    logger.info(
        "[notification] analysis complete | user=%s | investigation=%s | report_id=%s | findings=%d",
        user_email,
        investigation_name,
        report_id,
        finding_count,
    )
    _fire_and_forget(
        email_service.send_job_complete_email(user_email, investigation_name, finding_count)
    )


def send_job_failed(
    user_email: str,
    investigation_name: str,
    error_message: str,
) -> None:
    logger.warning(
        "[notification] analysis failed | user=%s | investigation=%s | error=%s",
        user_email,
        investigation_name,
        error_message[:500],
    )
    _fire_and_forget(
        email_service.send_job_failed_email(user_email, investigation_name, error_message)
    )

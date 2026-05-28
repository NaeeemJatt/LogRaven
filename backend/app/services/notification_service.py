# LogRaven — Job completion / failure notifications
#
# v1: structured application logs (ops can wire SES/SMTP later via env).

from app.utils.logger import get_logger

logger = get_logger(__name__)


def send_job_complete(
    user_email: str,
    investigation_name: str,
    report_id: str,
    finding_count: int,
) -> None:
    # TODO: wire to email/webhook when SMTP config is added
    logger.info(
        "[notification] analysis complete | user=%s | investigation=%s | report_id=%s | findings=%d",
        user_email,
        investigation_name,
        report_id,
        finding_count,
    )


def send_job_failed(
    user_email: str,
    investigation_name: str,
    error_message: str,
) -> None:
    # TODO: wire to email/webhook when SMTP config is added
    logger.warning(
        "[notification] analysis failed | user=%s | investigation=%s | error=%s",
        user_email,
        investigation_name,
        error_message[:500],
    )

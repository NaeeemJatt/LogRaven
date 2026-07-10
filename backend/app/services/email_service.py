# LogRaven — Email delivery (SMTP)
#
# Works with any SMTP provider (Amazon SES SMTP endpoint, Gmail, Mailgun...).
# When SMTP_HOST is not configured, emails are logged instead of sent so
# local development never silently swallows or fails on mail.
#
# Sending is executed in a thread (smtplib is blocking) so async callers
# never block the event loop.

from __future__ import annotations

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def is_email_configured() -> bool:
    return bool(settings.SMTP_HOST)


def _send_sync(to_email: str, subject: str, text_body: str, html_body: str | None) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())


async def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """Send an email. Returns True if delivered (or logged in dev mode)."""
    if not is_email_configured():
        logger.info(
            "[email:dev] to=%s | subject=%s | body=%s",
            to_email, subject, text_body.replace("\n", " ")[:500],
        )
        return True
    try:
        await asyncio.to_thread(_send_sync, to_email, subject, text_body, html_body)
        logger.info("[email] sent | to=%s | subject=%s", to_email, subject)
        return True
    except Exception as exc:
        logger.error("[email] delivery failed | to=%s | subject=%s | error=%s", to_email, subject, exc)
        return False


def _button_html(heading: str, body: str, link: str, button_label: str) -> str:
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#1a1a2e">
  <h2 style="margin:0 0 12px">{heading}</h2>
  <p style="line-height:1.6;color:#444">{body}</p>
  <p style="margin:24px 0">
    <a href="{link}" style="background:#4F46E5;color:#fff;padding:12px 22px;border-radius:8px;text-decoration:none;display:inline-block">{button_label}</a>
  </p>
  <p style="font-size:12px;color:#888">If the button doesn't work, copy this link into your browser:<br>{link}</p>
  <p style="font-size:12px;color:#888">If you didn't request this, you can safely ignore this email.</p>
</div>"""


async def send_verification_email(to_email: str, token: str) -> bool:
    link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?token={token}"
    return await send_email(
        to_email,
        "Verify your LogRaven email",
        f"Welcome to LogRaven!\n\nVerify your email address by opening this link:\n{link}\n\n"
        "The link expires in 24 hours. If you didn't create an account, ignore this email.",
        _button_html(
            "Verify your email",
            "Welcome to LogRaven. Confirm this email address to secure your account. The link expires in 24 hours.",
            link,
            "Verify email",
        ),
    )


async def send_password_reset_email(to_email: str, token: str) -> bool:
    link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={token}"
    return await send_email(
        to_email,
        "Reset your LogRaven password",
        f"A password reset was requested for your LogRaven account.\n\nReset it here:\n{link}\n\n"
        "The link expires in 1 hour. If you didn't request this, ignore this email — your password is unchanged.",
        _button_html(
            "Reset your password",
            "A password reset was requested for your LogRaven account. The link expires in 1 hour.",
            link,
            "Reset password",
        ),
    )


async def send_job_complete_email(to_email: str, investigation_name: str, finding_count: int) -> bool:
    link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/dashboard"
    return await send_email(
        to_email,
        f"LogRaven analysis complete — {investigation_name}",
        f"Your investigation '{investigation_name}' finished analyzing with {finding_count} finding(s).\n\n"
        f"View the report: {link}",
        _button_html(
            "Analysis complete",
            f"Your investigation <b>{investigation_name}</b> finished with {finding_count} finding(s).",
            link,
            "View report",
        ),
    )


async def send_job_failed_email(to_email: str, investigation_name: str, error_message: str) -> bool:
    link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/dashboard"
    return await send_email(
        to_email,
        f"LogRaven analysis failed — {investigation_name}",
        f"Your investigation '{investigation_name}' failed:\n{error_message[:500]}\n\n"
        f"You can retry from the dashboard: {link}",
        _button_html(
            "Analysis failed",
            f"Your investigation <b>{investigation_name}</b> failed: {error_message[:300]}",
            link,
            "Open dashboard",
        ),
    )

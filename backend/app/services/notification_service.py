# LogRaven — Notification Service
#
# PURPOSE:
#   Send email notifications for job completion and failure.
#   Uses AWS SES in production (same dependency as S3).
#   In development: just logs the notification content.
#
# FUNCTIONS:
#   send_job_complete(user, investigation, report) -> None
#     - Send email with summary and download link if job took > 30 seconds
#
#   send_job_failed(user, investigation, error_msg) -> None
#     - Send failure notification with generic user-facing message
#
# TODO Month 5: Implement this file.

# LogRaven — HIPAA Security Rule framework pack
#
# Technical and administrative safeguards (45 CFR Part 164 Subpart C) that AWS
# evidence can substantiate. Safeguards needing organizational evidence are
# marked automatable=False.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_ADMIN = "Administrative Safeguards (164.308)"
_TECH = "Technical Safeguards (164.312)"

CONTROLS = (
    Control("164.308(a)(1)", "Security management process / risk analysis", _ADMIN,
            signals=("config_recorder_enabled", "securityhub_enabled", "guardduty_enabled"),
            guidance="Run continuous risk analysis via Config, Security Hub, and GuardDuty."),
    Control("164.308(a)(3)", "Workforce security / authorization & supervision", _ADMIN,
            signals=("iam_admin_users", "iam_stale_access_keys"),
            guidance="Authorize and supervise workforce access; remove stale credentials."),
    Control("164.308(a)(4)", "Information access management", _ADMIN,
            signals=("iam_admin_users", "access_analyzer_external_findings"),
            guidance="Grant least-privilege access to ePHI and remediate external exposure."),
    Control("164.308(a)(5)", "Security awareness and training", _ADMIN, automatable=False,
            guidance="Provide security awareness training and periodic reminders."),
    Control("164.308(a)(6)", "Security incident procedures", _ADMIN,
            signals=("guardduty_high_severity_findings", "security_alarms_configured"),
            guidance="Detect, respond to, and document security incidents."),
    Control("164.308(a)(7)", "Contingency plan / data backup", _ADMIN,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Maintain data backup and disaster recovery plans."),
    Control("164.312(a)(1)", "Access control (unique user IDs, emergency access)", _TECH,
            signals=("iam_users_total", "iam_mfa_enforcement_rate"),
            guidance="Assign unique user identities and enforce access control with MFA."),
    Control("164.312(a)(2)(iv)", "Encryption and decryption of ePHI at rest", _TECH,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption", "kms_key_rotation_rate"),
            guidance="Encrypt ePHI at rest across S3/RDS/EBS with managed keys."),
    Control("164.312(b)", "Audit controls", _TECH,
            signals=("cloudtrail_multiregion", "cloudtrail_log_validation", "cloudwatch_log_retention_days"),
            guidance="Record and examine activity with CloudTrail and retained logs."),
    Control("164.312(c)(1)", "Integrity controls for ePHI", _TECH,
            signals=("cloudtrail_log_validation", "s3_public_access_blocked"),
            guidance="Protect ePHI from improper alteration; validate log integrity."),
    Control("164.312(d)", "Person or entity authentication", _TECH,
            signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled", "iam_password_policy_exists"),
            guidance="Verify identity with strong authentication and MFA."),
    Control("164.312(e)(1)", "Transmission security", _TECH,
            signals=("open_security_groups", "cloudtrail_encrypted"),
            guidance="Guard against unauthorized access to ePHI in transit."),
)

FRAMEWORK = Framework(
    id="hipaa",
    name="HIPAA Security Rule",
    version="45 CFR Part 164",
    description="HIPAA administrative and technical safeguards for protecting electronic PHI.",
    controls=CONTROLS,
)

register(FRAMEWORK)

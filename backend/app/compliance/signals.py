# LogRaven — Normalized Compliance Evidence Signals
#
# The "collect once, map to many" core. Collectors produce PII-free evidence;
# this module flattens that evidence into a single namespace of named signals.
# Framework controls (in frameworks/*.py) reference these signal keys, so one
# evidence collection run can be graded against any number of frameworks.
#
# Every signal value is an aggregate (count / bool / percentage) — never PII.

from __future__ import annotations

from typing import Any

# Canonical signal catalog: key -> human-readable description.
# Keep this in sync with the collectors (sanitizer + collectors/aws_extended).
SIGNAL_CATALOG: dict[str, str] = {
    # Identity & access management
    "iam_mfa_enforcement_rate": "Percentage of IAM users with MFA enabled",
    "iam_root_mfa_enabled": "Whether the AWS root account has MFA enabled",
    "iam_password_policy_exists": "Whether an account password policy is configured",
    "iam_password_min_length": "Minimum password length required by policy",
    "iam_users_total": "Total number of IAM users",
    "iam_stale_access_keys": "Access keys older than 90 days or unused",
    "iam_admin_users": "Users/principals with administrative privileges",
    "access_analyzer_external_findings": "IAM Access Analyzer findings exposing resources externally",
    # Logging, monitoring & detection
    "cloudtrail_multiregion": "A multi-region CloudTrail trail is enabled",
    "cloudtrail_log_validation": "CloudTrail log file integrity validation is enabled",
    "cloudtrail_encrypted": "CloudTrail logs are encrypted with KMS",
    "cloudwatch_log_retention_days": "Minimum CloudWatch log group retention in days",
    "config_recorder_enabled": "AWS Config configuration recorder is enabled",
    "securityhub_enabled": "AWS Security Hub is enabled",
    "guardduty_enabled": "Amazon GuardDuty threat detection is enabled",
    "guardduty_high_severity_findings": "Count of high-severity GuardDuty findings",
    "inspector_enabled": "Amazon Inspector vulnerability scanning is enabled",
    "security_alarms_configured": "CloudWatch alarms exist for security-relevant metrics",
    # Encryption & data protection
    "s3_default_encryption_rate": "Percentage of S3 buckets with default encryption",
    "s3_public_access_blocked": "Account-level S3 public access block is enabled",
    "ebs_default_encryption": "EBS default encryption is enabled in the region",
    "rds_encryption_rate": "Percentage of RDS instances encrypted at rest",
    "kms_key_rotation_rate": "Percentage of customer KMS keys with rotation enabled",
    # Network security
    "vpc_flow_logs_enabled": "VPC flow logs are enabled",
    "open_security_groups": "Security groups open to 0.0.0.0/0 on sensitive ports",
    "default_sg_restricted": "Default security groups deny all traffic",
    # Resilience & availability
    "backup_configured": "AWS Backup plans are configured",
    "rds_backups_enabled": "RDS automated backups are enabled",
    # Activity / behavioural
    "failed_login_attempts": "Failed console login attempts in the audit window",
    "off_hours_events": "Privileged actions occurring outside business hours",
    "privilege_escalation_events": "Privilege escalation (AssumeRole) events",
    "policy_change_events": "IAM / resource policy change events",
}

# Sentinel used when a signal could not be collected (e.g. missing IAM permission).
UNKNOWN = None


def _get(section: dict[str, Any] | None, key: str, default: Any = UNKNOWN) -> Any:
    if not isinstance(section, dict):
        return default
    value = section.get(key)
    return default if value is None else value


def build_evidence_signals(sanitized: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten sanitized evidence sections into the canonical signal namespace.

    Missing sections/keys resolve to None (UNKNOWN) so frameworks can still be
    graded on whatever evidence is available. No PII ever enters this dict.
    """
    ct = sanitized.get("cloudtrail") or {}
    iam = sanitized.get("iam") or {}
    gd = sanitized.get("guardduty") or {}
    iam_ext = sanitized.get("iam_extended") or {}
    ct_cfg = sanitized.get("cloudtrail_config") or {}
    enc = sanitized.get("encryption") or {}
    net = sanitized.get("network") or {}
    mon = sanitized.get("monitoring") or {}
    backup = sanitized.get("backup") or {}

    signals: dict[str, Any] = {
        # Identity & access
        "iam_mfa_enforcement_rate": _get(iam, "mfa_enforcement_rate_percent"),
        "iam_root_mfa_enabled": _get(iam, "root_mfa_enabled"),
        "iam_password_policy_exists": _get(iam, "password_policy_exists"),
        "iam_password_min_length": _get(iam, "password_min_length"),
        "iam_users_total": _get(iam, "total_users"),
        "iam_stale_access_keys": _get(iam_ext, "stale_access_keys"),
        "iam_admin_users": _get(iam_ext, "admin_users"),
        "access_analyzer_external_findings": _get(iam_ext, "access_analyzer_external_findings"),
        # Logging & monitoring
        "cloudtrail_multiregion": _get(ct_cfg, "multi_region"),
        "cloudtrail_log_validation": _get(ct_cfg, "log_file_validation"),
        "cloudtrail_encrypted": _get(ct_cfg, "kms_encrypted"),
        "cloudwatch_log_retention_days": _get(mon, "min_log_retention_days"),
        "config_recorder_enabled": _get(mon, "config_recorder_enabled"),
        "securityhub_enabled": _get(mon, "securityhub_enabled"),
        "guardduty_enabled": _get(gd, "enabled"),
        "guardduty_high_severity_findings": _get(gd, "high_severity_findings"),
        "inspector_enabled": _get(mon, "inspector_enabled"),
        "security_alarms_configured": _get(mon, "security_alarms_configured"),
        # Encryption
        "s3_default_encryption_rate": _get(enc, "s3_default_encryption_rate"),
        "s3_public_access_blocked": _get(enc, "s3_public_access_blocked"),
        "ebs_default_encryption": _get(enc, "ebs_default_encryption"),
        "rds_encryption_rate": _get(enc, "rds_encryption_rate"),
        "kms_key_rotation_rate": _get(enc, "kms_key_rotation_rate"),
        # Network
        "vpc_flow_logs_enabled": _get(net, "vpc_flow_logs_enabled"),
        "open_security_groups": _get(net, "open_security_groups"),
        "default_sg_restricted": _get(net, "default_sg_restricted"),
        # Resilience
        "backup_configured": _get(backup, "backup_configured"),
        "rds_backups_enabled": _get(backup, "rds_backups_enabled"),
        # Activity
        "failed_login_attempts": _get(ct, "failed_login_attempts"),
        "off_hours_events": _get(ct, "off_hours_events"),
        "privilege_escalation_events": _get(ct, "privilege_escalation_events"),
        "policy_change_events": _get(ct, "policy_change_events"),
    }
    return signals


def select_signals(all_signals: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Return only the signals relevant to a control (preserving UNKNOWN)."""
    return {key: all_signals.get(key) for key in keys}

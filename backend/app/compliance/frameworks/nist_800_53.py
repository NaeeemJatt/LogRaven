# LogRaven — NIST SP 800-53 Rev. 5 framework pack (AWS-addressable subset)
#
# A subset of the moderate baseline control families that AWS technical evidence
# can substantiate (AC, AU, CM, IA, SC, SI, CP).

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_AC = "AC — Access Control"
_AU = "AU — Audit and Accountability"
_CM = "CM — Configuration Management"
_IA = "IA — Identification and Authentication"
_SC = "SC — System and Communications Protection"
_SI = "SI — System and Information Integrity"
_CP = "CP — Contingency Planning"

CONTROLS = (
    Control("AC-2", "Account Management", _AC,
            signals=("iam_users_total", "iam_stale_access_keys", "iam_admin_users"),
            guidance="Manage account lifecycle; disable unused accounts and limit privileged accounts."),
    Control("AC-6", "Least Privilege", _AC,
            signals=("iam_admin_users", "access_analyzer_external_findings"),
            guidance="Enforce least privilege and remediate over-permissive access."),
    Control("AC-17", "Remote Access", _AC,
            signals=("open_security_groups", "iam_mfa_enforcement_rate"),
            guidance="Restrict and authenticate remote access; close open admin ports."),
    Control("AU-2", "Event Logging", _AU,
            signals=("cloudtrail_multiregion", "vpc_flow_logs_enabled"),
            guidance="Log security-relevant events across all regions."),
    Control("AU-9", "Protection of Audit Information", _AU,
            signals=("cloudtrail_log_validation", "cloudtrail_encrypted"),
            guidance="Protect audit logs with integrity validation and encryption."),
    Control("AU-11", "Audit Record Retention", _AU,
            signals=("cloudwatch_log_retention_days",),
            guidance="Retain audit records per policy."),
    Control("CM-2", "Baseline Configuration", _CM,
            signals=("config_recorder_enabled", "default_sg_restricted"),
            guidance="Maintain and monitor secure baseline configurations."),
    Control("CM-6", "Configuration Settings", _CM,
            signals=("config_recorder_enabled", "securityhub_enabled"),
            guidance="Enforce secure configuration settings and detect drift."),
    Control("IA-2", "Identification and Authentication (Organizational Users)", _IA,
            signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled"),
            guidance="Uniquely identify and MFA-authenticate users."),
    Control("IA-5", "Authenticator Management", _IA,
            signals=("iam_password_policy_exists", "iam_password_min_length", "iam_stale_access_keys"),
            guidance="Manage authenticators: strong password policy, rotate/remove stale keys."),
    Control("SC-7", "Boundary Protection", _SC,
            signals=("open_security_groups", "default_sg_restricted", "vpc_flow_logs_enabled"),
            guidance="Protect external boundaries; restrict and monitor traffic."),
    Control("SC-13", "Cryptographic Protection", _SC,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption", "kms_key_rotation_rate"),
            guidance="Use approved cryptography for data at rest; rotate keys."),
    Control("SC-28", "Protection of Information at Rest", _SC,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption"),
            guidance="Encrypt information at rest across data stores."),
    Control("SI-4", "System Monitoring", _SI,
            signals=("guardduty_enabled", "security_alarms_configured", "vpc_flow_logs_enabled"),
            guidance="Continuously monitor systems for indicators of compromise."),
    Control("SI-2", "Flaw Remediation", _SI,
            signals=("inspector_enabled", "guardduty_high_severity_findings"),
            guidance="Identify and remediate system flaws (Inspector)."),
    Control("CP-9", "System Backup", _CP,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Conduct backups of system and data."),
)

FRAMEWORK = Framework(
    id="nist_800_53",
    name="NIST SP 800-53 Rev. 5",
    version="Rev. 5 (Moderate subset)",
    description="NIST 800-53 security control families substantiated by AWS evidence (AWS-addressable subset).",
    controls=CONTROLS,
)

register(FRAMEWORK)

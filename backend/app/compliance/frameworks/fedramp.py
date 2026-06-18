# LogRaven — FedRAMP Moderate framework pack (AWS-addressable subset)
#
# FedRAMP baselines build on NIST 800-53. This pack surfaces the technically
# verifiable controls most relevant to a cloud service offering on AWS.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_AC = "Access Control"
_AU = "Audit and Accountability"
_IA = "Identification and Authentication"
_SC = "System and Communications Protection"
_SI = "System and Information Integrity"
_CM = "Configuration Management"
_CP = "Contingency Planning"

CONTROLS = (
    Control("AC-2(FR)", "Account Management", _AC,
            signals=("iam_users_total", "iam_stale_access_keys", "iam_admin_users"),
            guidance="Manage accounts and remove stale/over-privileged access."),
    Control("AC-6(FR)", "Least Privilege", _AC,
            signals=("iam_admin_users", "access_analyzer_external_findings"),
            guidance="Enforce least privilege; remediate external exposure."),
    Control("IA-2(FR)", "MFA for Network Access to Privileged Accounts", _IA,
            signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled"),
            guidance="Require MFA for privileged and network access."),
    Control("AU-2(FR)", "Event Logging", _AU,
            signals=("cloudtrail_multiregion", "vpc_flow_logs_enabled"),
            guidance="Enable comprehensive multi-region logging."),
    Control("AU-9(FR)", "Protection of Audit Information", _AU,
            signals=("cloudtrail_log_validation", "cloudtrail_encrypted"),
            guidance="Validate and encrypt audit logs."),
    Control("CM-6(FR)", "Configuration Settings", _CM,
            signals=("config_recorder_enabled", "securityhub_enabled", "default_sg_restricted"),
            guidance="Enforce and monitor secure baselines."),
    Control("SC-7(FR)", "Boundary Protection", _SC,
            signals=("open_security_groups", "default_sg_restricted", "vpc_flow_logs_enabled"),
            guidance="Protect and monitor the system boundary."),
    Control("SC-28(FR)", "Protection of Information at Rest", _SC,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption", "kms_key_rotation_rate"),
            guidance="Encrypt FedRAMP data at rest with rotated keys."),
    Control("SI-4(FR)", "System Monitoring", _SI,
            signals=("guardduty_enabled", "security_alarms_configured"),
            guidance="Continuously monitor for threats and anomalies."),
    Control("SI-2(FR)", "Flaw Remediation", _SI,
            signals=("inspector_enabled", "guardduty_high_severity_findings"),
            guidance="Scan for and remediate vulnerabilities."),
    Control("CP-9(FR)", "System Backup", _CP,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Back up systems and data for recovery."),
)

FRAMEWORK = Framework(
    id="fedramp",
    name="FedRAMP Moderate",
    version="Rev. 5 baseline subset",
    description="FedRAMP Moderate baseline controls (NIST 800-53 derived) addressable by AWS technical evidence.",
    controls=CONTROLS,
)

register(FRAMEWORK)

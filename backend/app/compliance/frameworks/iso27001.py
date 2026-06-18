# LogRaven — ISO/IEC 27001:2022 Annex A framework pack
#
# Focused on the Annex A controls that AWS technical evidence can substantiate.
# Controls that require organizational/manual evidence are marked automatable=False
# so the UI can show honest coverage.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_ORG = "A.5 — Organizational"
_PEOPLE = "A.6 — People"
_PHYS = "A.7 — Physical"
_TECH = "A.8 — Technological"

CONTROLS = (
    Control("A.5.1", "Policies for information security", _ORG, automatable=False,
            guidance="Maintain and approve an information security policy set reviewed at planned intervals."),
    Control("A.5.15", "Access control", _TECH,
            signals=("iam_mfa_enforcement_rate", "iam_admin_users", "iam_password_policy_exists"),
            guidance="Enforce least-privilege access control with MFA and a password policy."),
    Control("A.5.16", "Identity management", _TECH,
            signals=("iam_users_total", "iam_stale_access_keys"),
            guidance="Manage the full identity lifecycle and remove unused identities/keys."),
    Control("A.5.17", "Authentication information", _TECH,
            signals=("iam_password_policy_exists", "iam_password_min_length", "iam_mfa_enforcement_rate"),
            guidance="Require strong authentication and MFA for all accounts."),
    Control("A.5.18", "Access rights", _TECH,
            signals=("iam_admin_users", "access_analyzer_external_findings"),
            guidance="Provision, review, and revoke access rights; remediate external exposure."),
    Control("A.5.23", "Information security for use of cloud services", _ORG,
            signals=("s3_public_access_blocked", "config_recorder_enabled", "securityhub_enabled"),
            guidance="Govern cloud configuration with Config/Security Hub and block public access."),
    Control("A.5.24", "Information security incident management planning", _ORG, automatable=False,
            guidance="Define an incident management process with roles and response procedures."),
    Control("A.5.25", "Assessment and decision on information security events", _ORG,
            signals=("guardduty_high_severity_findings", "securityhub_enabled"),
            guidance="Assess detected events via GuardDuty/Security Hub and decide on incidents."),
    Control("A.6.3", "Information security awareness, education and training", _PEOPLE, automatable=False,
            guidance="Run regular security awareness training for all personnel."),
    Control("A.8.2", "Privileged access rights", _TECH,
            signals=("iam_admin_users", "iam_root_mfa_enabled"),
            guidance="Minimize and protect privileged accounts; enable root MFA."),
    Control("A.8.5", "Secure authentication", _TECH,
            signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled"),
            guidance="Implement MFA-based secure authentication for users and root."),
    Control("A.8.8", "Management of technical vulnerabilities", _TECH,
            signals=("inspector_enabled", "guardduty_high_severity_findings", "config_recorder_enabled"),
            guidance="Continuously identify and remediate vulnerabilities (Inspector, Config)."),
    Control("A.8.9", "Configuration management", _TECH,
            signals=("config_recorder_enabled", "securityhub_enabled", "default_sg_restricted"),
            guidance="Track and enforce secure baseline configurations with AWS Config."),
    Control("A.8.12", "Data leakage prevention", _TECH,
            signals=("s3_public_access_blocked", "access_analyzer_external_findings", "open_security_groups"),
            guidance="Prevent data exfiltration paths: block public S3, close open ports."),
    Control("A.8.13", "Information backup", _TECH,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Configure automated backups (AWS Backup, RDS automated backups)."),
    Control("A.8.15", "Logging", _TECH,
            signals=("cloudtrail_multiregion", "cloudtrail_log_validation", "cloudwatch_log_retention_days"),
            guidance="Enable multi-region CloudTrail with integrity validation and retention."),
    Control("A.8.16", "Monitoring activities", _TECH,
            signals=("guardduty_enabled", "vpc_flow_logs_enabled", "security_alarms_configured"),
            guidance="Continuously monitor with GuardDuty, VPC flow logs, and alarms."),
    Control("A.8.20", "Networks security", _TECH,
            signals=("open_security_groups", "default_sg_restricted", "vpc_flow_logs_enabled"),
            guidance="Secure network boundaries; restrict security groups and log flows."),
    Control("A.8.24", "Use of cryptography", _TECH,
            signals=("s3_default_encryption_rate", "ebs_default_encryption", "rds_encryption_rate", "kms_key_rotation_rate"),
            guidance="Encrypt data at rest across S3/EBS/RDS and rotate KMS keys."),
)

FRAMEWORK = Framework(
    id="iso27001",
    name="ISO/IEC 27001:2022",
    version="2022 Annex A",
    description="Information security management system controls (Annex A) substantiated by AWS technical evidence.",
    controls=CONTROLS,
)

register(FRAMEWORK)

# LogRaven — NIST Cybersecurity Framework 2.0 pack
#
# Organized by the six CSF functions. Outcomes substantiated by AWS evidence;
# governance outcomes are marked automatable=False.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_GV = "GOVERN"
_ID = "IDENTIFY"
_PR = "PROTECT"
_DE = "DETECT"
_RS = "RESPOND"
_RC = "RECOVER"

CONTROLS = (
    Control("GV.OC", "Organizational context & cybersecurity governance", _GV, automatable=False,
            guidance="Establish and communicate cybersecurity governance and risk strategy."),
    Control("ID.AM", "Asset management & inventory", _ID,
            signals=("config_recorder_enabled",),
            guidance="Maintain an asset inventory via AWS Config."),
    Control("ID.RA", "Risk assessment", _ID,
            signals=("inspector_enabled", "securityhub_enabled", "guardduty_high_severity_findings"),
            guidance="Continuously assess risk (Inspector, Security Hub)."),
    Control("PR.AA", "Identity management, authentication, and access control", _PR,
            signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled", "iam_admin_users", "iam_password_policy_exists"),
            guidance="Enforce strong identity and access controls with MFA and least privilege."),
    Control("PR.DS", "Data security (encryption at rest/in transit)", _PR,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption", "kms_key_rotation_rate"),
            guidance="Encrypt data at rest and manage keys."),
    Control("PR.PS", "Platform security & secure configuration", _PR,
            signals=("config_recorder_enabled", "default_sg_restricted", "open_security_groups"),
            guidance="Harden platform configuration and restrict network exposure."),
    Control("PR.IR", "Technology infrastructure resilience", _PR,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Build resilient infrastructure with backups."),
    Control("DE.CM", "Continuous monitoring", _DE,
            signals=("guardduty_enabled", "vpc_flow_logs_enabled", "cloudtrail_multiregion", "security_alarms_configured"),
            guidance="Continuously monitor networks and accounts."),
    Control("DE.AE", "Adverse event analysis", _DE,
            signals=("guardduty_high_severity_findings", "securityhub_enabled", "failed_login_attempts"),
            guidance="Analyze detected events to characterize incidents."),
    Control("RS.MA", "Incident management & response", _RS,
            signals=("security_alarms_configured",),
            automatable=False,
            guidance="Execute and improve an incident response process."),
    Control("RC.RP", "Incident recovery plan execution", _RC,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Restore systems and data from backups during recovery."),
)

FRAMEWORK = Framework(
    id="nist_csf",
    name="NIST CSF",
    version="2.0",
    description="NIST Cybersecurity Framework 2.0 functions (Govern, Identify, Protect, Detect, Respond, Recover).",
    controls=CONTROLS,
)

register(FRAMEWORK)

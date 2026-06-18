# LogRaven — CSA Cloud Controls Matrix (CCM) v4 pack (AWS-addressable subset)
#
# Selected CCM domains substantiated by AWS technical evidence.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_IAM = "IAM — Identity & Access Management"
_CEK = "CEK — Cryptography, Encryption & Key Management"
_LOG = "LOG — Logging & Monitoring"
_IVS = "IVS — Infrastructure & Virtualization Security"
_DSP = "DSP — Data Security & Privacy"
_BCR = "BCR — Business Continuity & Resilience"

CONTROLS = (
    Control("IAM-03", "Identity inventory & lifecycle", _IAM,
            signals=("iam_users_total", "iam_stale_access_keys"),
            guidance="Maintain an identity inventory and remove stale credentials."),
    Control("IAM-08", "Privileged access management", _IAM,
            signals=("iam_admin_users", "iam_root_mfa_enabled"),
            guidance="Restrict and protect privileged access; enable root MFA."),
    Control("IAM-14", "Strong authentication (MFA)", _IAM,
            signals=("iam_mfa_enforcement_rate", "iam_password_policy_exists"),
            guidance="Enforce MFA and strong password policy."),
    Control("CEK-03", "Data encryption at rest", _CEK,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption"),
            guidance="Encrypt data at rest across all stores."),
    Control("CEK-08", "Cryptographic key rotation", _CEK,
            signals=("kms_key_rotation_rate",),
            guidance="Rotate cryptographic keys regularly."),
    Control("LOG-03", "Security monitoring & alerting", _LOG,
            signals=("guardduty_enabled", "security_alarms_configured", "guardduty_high_severity_findings"),
            guidance="Monitor and alert on security events."),
    Control("LOG-05", "Audit logs protection & retention", _LOG,
            signals=("cloudtrail_multiregion", "cloudtrail_log_validation", "cloudwatch_log_retention_days"),
            guidance="Protect and retain audit logs."),
    Control("IVS-03", "Network security & segmentation", _IVS,
            signals=("open_security_groups", "default_sg_restricted", "vpc_flow_logs_enabled"),
            guidance="Segment and monitor networks; restrict exposure."),
    Control("IVS-04", "Secure configuration baselines", _IVS,
            signals=("config_recorder_enabled", "securityhub_enabled"),
            guidance="Enforce and monitor secure baselines."),
    Control("DSP-17", "Sensitive data protection & exposure", _DSP,
            signals=("s3_public_access_blocked", "access_analyzer_external_findings"),
            guidance="Prevent public/external exposure of sensitive data."),
    Control("BCR-08", "Backup & recovery", _BCR,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Maintain backups enabling recovery."),
)

FRAMEWORK = Framework(
    id="csa_ccm",
    name="CSA Cloud Controls Matrix",
    version="v4",
    description="Cloud Security Alliance CCM v4 domains addressable by AWS technical evidence.",
    controls=CONTROLS,
)

register(FRAMEWORK)

# LogRaven — PCI DSS v4.0 framework pack
#
# Infrastructure-addressable requirements (Req 1, 2, 3, 7, 8, 10). Requirements
# needing process/physical evidence are marked automatable=False.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_NET = "Req 1 — Network Security Controls"
_CFG = "Req 2 — Secure Configurations"
_ENC = "Req 3 — Protect Stored Account Data"
_ACCESS = "Req 7 — Restrict Access by Need to Know"
_AUTH = "Req 8 — Identify Users and Authenticate Access"
_LOG = "Req 10 — Log and Monitor Access"

CONTROLS = (
    Control("1.2", "Network security controls configuration restricts traffic", _NET,
            signals=("open_security_groups", "default_sg_restricted"),
            guidance="Restrict inbound/outbound traffic; remove 0.0.0.0/0 rules on sensitive ports."),
    Control("1.3", "Network access to/from the cardholder data environment is restricted", _NET,
            signals=("open_security_groups", "vpc_flow_logs_enabled"),
            guidance="Segment the CDE and log network flows with VPC flow logs."),
    Control("2.2", "System components are configured and managed securely", _CFG,
            signals=("config_recorder_enabled", "securityhub_enabled", "default_sg_restricted"),
            guidance="Apply and monitor secure configuration baselines (Config/Security Hub)."),
    Control("3.5", "Primary account number is secured wherever stored", _ENC,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption"),
            guidance="Encrypt stored account data at rest across S3/RDS/EBS."),
    Control("3.6", "Cryptographic keys protecting stored account data are secured", _ENC,
            signals=("kms_key_rotation_rate", "cloudtrail_encrypted"),
            guidance="Protect and rotate cryptographic keys (KMS rotation)."),
    Control("7.2", "Access to system components and data is appropriately restricted", _ACCESS,
            signals=("iam_admin_users", "access_analyzer_external_findings"),
            guidance="Enforce least privilege and remediate external-access findings."),
    Control("8.3", "Strong authentication for users and administrators is established", _AUTH,
            signals=("iam_password_policy_exists", "iam_password_min_length"),
            guidance="Require strong passwords meeting PCI complexity and length rules."),
    Control("8.4", "Multi-factor authentication is implemented for access", _AUTH,
            signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled"),
            guidance="Enforce MFA for all access into the environment, including root."),
    Control("8.6", "Use of application and system accounts is managed", _AUTH,
            signals=("iam_stale_access_keys", "iam_users_total"),
            guidance="Manage and rotate service/application credentials; remove stale keys."),
    Control("10.2", "Audit logs capture all access to system components", _LOG,
            signals=("cloudtrail_multiregion", "cloudtrail_log_validation"),
            guidance="Enable a multi-region CloudTrail with log file validation."),
    Control("10.4", "Audit logs are reviewed to identify anomalies or suspicious activity", _LOG,
            signals=("guardduty_enabled", "security_alarms_configured", "guardduty_high_severity_findings"),
            guidance="Automate log review with GuardDuty and CloudWatch alarms."),
    Control("10.5", "Audit log history is retained and protected", _LOG,
            signals=("cloudwatch_log_retention_days", "cloudtrail_encrypted"),
            guidance="Retain logs for at least 12 months and protect them from tampering."),
    Control("12.10", "Suspected and confirmed security incidents are responded to", "Req 12 — Support Policies",
            automatable=False,
            guidance="Maintain and test an incident response plan."),
)

FRAMEWORK = Framework(
    id="pci_dss",
    name="PCI DSS",
    version="v4.0",
    description="Payment Card Industry Data Security Standard — infrastructure-addressable requirements.",
    controls=CONTROLS,
)

register(FRAMEWORK)

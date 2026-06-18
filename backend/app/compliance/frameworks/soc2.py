# LogRaven — SOC 2 (AICPA Trust Service Criteria) framework pack
#
# Kept at the same CC6/CC7 controls as the original auditor so existing SOC 2
# audits produce an identical control set; enriched with evidence-signal
# mappings and remediation guidance for the generalized engine.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

CONTROLS = (
    Control(
        control_id="CC6.1",
        name="Logical access security software, infrastructure, and architectures",
        category="CC6 — Logical & Physical Access",
        signals=(
            "iam_mfa_enforcement_rate", "iam_root_mfa_enabled", "iam_password_policy_exists",
            "iam_password_min_length", "s3_public_access_blocked", "default_sg_restricted",
            "open_security_groups",
        ),
        guidance="Enforce MFA for all users and root, set a strong password policy, and restrict default security groups.",
    ),
    Control(
        control_id="CC6.2",
        name="New internal and external users are registered and authorized",
        category="CC6 — Logical & Physical Access",
        signals=("iam_users_total", "iam_mfa_enforcement_rate", "iam_admin_users"),
        guidance="Provision users through an approved process and grant least-privilege access.",
    ),
    Control(
        control_id="CC6.3",
        name="Internal and external users are removed when no longer authorized",
        category="CC6 — Logical & Physical Access",
        signals=("iam_stale_access_keys", "iam_users_total"),
        guidance="Disable unused access keys and deprovision users promptly on offboarding.",
    ),
    Control(
        control_id="CC6.6",
        name="Logical access restrictions to systems protecting against external threats",
        category="CC6 — Logical & Physical Access",
        signals=(
            "open_security_groups", "default_sg_restricted", "vpc_flow_logs_enabled",
            "access_analyzer_external_findings", "s3_public_access_blocked",
        ),
        guidance="Close security groups open to the internet and remediate Access Analyzer external-exposure findings.",
    ),
    Control(
        control_id="CC6.7",
        name="Transmission, movement, and removal of information is restricted",
        category="CC6 — Logical & Physical Access",
        signals=(
            "s3_default_encryption_rate", "ebs_default_encryption", "rds_encryption_rate",
            "kms_key_rotation_rate", "cloudtrail_encrypted",
        ),
        guidance="Enable encryption at rest for S3, EBS, and RDS, and enable KMS key rotation.",
    ),
    Control(
        control_id="CC6.8",
        name="Controls to prevent or detect unauthorized or malicious software",
        category="CC6 — Logical & Physical Access",
        signals=("guardduty_enabled", "inspector_enabled", "guardduty_high_severity_findings"),
        guidance="Enable GuardDuty and Inspector to detect malicious activity and vulnerable software.",
    ),
    Control(
        control_id="CC7.1",
        name="Vulnerability management program",
        category="CC7 — System Operations",
        signals=("inspector_enabled", "securityhub_enabled", "config_recorder_enabled"),
        guidance="Run continuous vulnerability scanning (Inspector) and enable Security Hub + AWS Config.",
    ),
    Control(
        control_id="CC7.2",
        name="System components are monitored to detect anomalies",
        category="CC7 — System Operations",
        signals=(
            "guardduty_enabled", "cloudtrail_multiregion", "vpc_flow_logs_enabled",
            "security_alarms_configured", "cloudwatch_log_retention_days",
        ),
        guidance="Enable a multi-region CloudTrail, VPC flow logs, GuardDuty, and CloudWatch security alarms.",
    ),
    Control(
        control_id="CC7.3",
        name="Evaluate security events to determine if they are incidents",
        category="CC7 — System Operations",
        signals=("guardduty_high_severity_findings", "securityhub_enabled", "failed_login_attempts"),
        guidance="Triage GuardDuty/Security Hub findings and investigate anomalous login activity.",
    ),
    Control(
        control_id="CC7.4",
        name="Identified security incidents are contained and remediated",
        category="CC7 — System Operations",
        signals=("guardduty_high_severity_findings", "security_alarms_configured"),
        guidance="Define and exercise an incident response plan with automated alerting.",
    ),
    Control(
        control_id="CC7.5",
        name="Identified vulnerabilities are remediated",
        category="CC7 — System Operations",
        signals=("inspector_enabled", "guardduty_high_severity_findings", "config_recorder_enabled"),
        guidance="Track and remediate findings to closure with AWS Config conformance monitoring.",
    ),
)

FRAMEWORK = Framework(
    id="soc2",
    name="SOC 2 Type II",
    version="2017 TSC",
    description="AICPA Trust Service Criteria — Common Criteria CC6 (Logical & Physical Access) and CC7 (System Operations).",
    controls=CONTROLS,
)

register(FRAMEWORK)

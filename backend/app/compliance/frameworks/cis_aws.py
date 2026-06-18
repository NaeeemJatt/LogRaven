# LogRaven — CIS Amazon Web Services Foundations Benchmark pack
#
# The most directly AWS-native framework: nearly 1:1 with collected signals.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_IAM = "1 — Identity and Access Management"
_STORAGE = "2 — Storage"
_LOGGING = "3 — Logging"
_MONITOR = "4 — Monitoring"
_NETWORK = "5 — Networking"

CONTROLS = (
    Control("1.4", "Ensure no 'root' user account access key exists / root MFA enabled", _IAM,
            signals=("iam_root_mfa_enabled",),
            guidance="Enable MFA on the root account and remove any root access keys."),
    Control("1.5", "Ensure MFA is enabled for the 'root' user account", _IAM,
            signals=("iam_root_mfa_enabled",),
            guidance="Enable hardware or virtual MFA for the root user."),
    Control("1.8", "Ensure IAM password policy requires minimum length of 14 or greater", _IAM,
            signals=("iam_password_policy_exists", "iam_password_min_length"),
            guidance="Set a password policy with minimum length >= 14."),
    Control("1.10", "Ensure MFA is enabled for all IAM users with a console password", _IAM,
            signals=("iam_mfa_enforcement_rate",),
            guidance="Require MFA for every console user."),
    Control("1.12", "Ensure credentials unused for 45 days or greater are disabled", _IAM,
            signals=("iam_stale_access_keys",),
            guidance="Disable access keys and credentials unused for 45+ days."),
    Control("1.16", "Ensure IAM policies that allow full administrative privileges are not attached", _IAM,
            signals=("iam_admin_users",),
            guidance="Avoid attaching full '*:*' administrative policies; use least privilege."),
    Control("1.20", "Ensure IAM Access Analyzer is enabled", _IAM,
            signals=("access_analyzer_external_findings",),
            guidance="Enable IAM Access Analyzer and remediate external-access findings."),
    Control("2.1.1", "Ensure S3 buckets employ encryption-at-rest", _STORAGE,
            signals=("s3_default_encryption_rate",),
            guidance="Enable default encryption on all S3 buckets."),
    Control("2.1.2", "Ensure S3 Block Public Access is enabled (account level)", _STORAGE,
            signals=("s3_public_access_blocked",),
            guidance="Enable account-level S3 Block Public Access."),
    Control("2.2.1", "Ensure EBS volume encryption is enabled", _STORAGE,
            signals=("ebs_default_encryption",),
            guidance="Enable EBS default encryption in every region."),
    Control("2.3.1", "Ensure encryption is enabled for RDS instances", _STORAGE,
            signals=("rds_encryption_rate",),
            guidance="Enable storage encryption for all RDS instances."),
    Control("3.1", "Ensure CloudTrail is enabled in all regions", _LOGGING,
            signals=("cloudtrail_multiregion",),
            guidance="Create a multi-region CloudTrail trail."),
    Control("3.2", "Ensure CloudTrail log file validation is enabled", _LOGGING,
            signals=("cloudtrail_log_validation",),
            guidance="Enable log file integrity validation on the trail."),
    Control("3.5", "Ensure CloudTrail logs are encrypted at rest using KMS CMKs", _LOGGING,
            signals=("cloudtrail_encrypted",),
            guidance="Configure the trail to encrypt logs with a KMS key."),
    Control("3.6", "Ensure rotation for customer-created KMS keys is enabled", _LOGGING,
            signals=("kms_key_rotation_rate",),
            guidance="Enable annual rotation on customer-managed KMS keys."),
    Control("3.7", "Ensure VPC flow logging is enabled in all VPCs", _LOGGING,
            signals=("vpc_flow_logs_enabled",),
            guidance="Enable VPC flow logs for all VPCs."),
    Control("4.1", "Ensure a log metric filter and alarm exist for unauthorized API calls", _MONITOR,
            signals=("security_alarms_configured", "cloudwatch_log_retention_days"),
            guidance="Create CloudWatch metric filters and alarms for security events."),
    Control("4.16", "Ensure AWS Security Hub is enabled", _MONITOR,
            signals=("securityhub_enabled",),
            guidance="Enable AWS Security Hub for centralized findings."),
    Control("4.x", "Ensure GuardDuty is enabled", _MONITOR,
            signals=("guardduty_enabled", "guardduty_high_severity_findings"),
            guidance="Enable Amazon GuardDuty and triage findings."),
    Control("5.2", "Ensure no security groups allow ingress from 0.0.0.0/0 to remote server admin ports", _NETWORK,
            signals=("open_security_groups",),
            guidance="Remove 0.0.0.0/0 ingress rules on ports 22/3389 and other admin ports."),
    Control("5.4", "Ensure the default security group of every VPC restricts all traffic", _NETWORK,
            signals=("default_sg_restricted",),
            guidance="Configure default security groups to deny all inbound/outbound traffic."),
)

FRAMEWORK = Framework(
    id="cis_aws",
    name="CIS AWS Foundations Benchmark",
    version="v3.0",
    description="Center for Internet Security AWS Foundations Benchmark — prescriptive AWS hardening checks.",
    controls=CONTROLS,
)

register(FRAMEWORK)

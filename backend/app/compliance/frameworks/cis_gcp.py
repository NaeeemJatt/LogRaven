# LogRaven — CIS Google Cloud Platform Foundation Benchmark pack
#
# Center for Internet Security (CIS) GCP Foundations Benchmark v3.0

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_IAM = "1 — Identity and Access Management"
_STORAGE = "2 — Storage"
_LOGGING = "3 — Logging and Monitoring"
_NETWORK = "4 — Networking"
_COMPUTE = "5 — Virtual Machines"

CONTROLS = (
    Control(
        "1.1",
        "Ensure Corporate Login Credentials are Used Instead of Personal Gmail Accounts",
        _IAM,
        signals=("iam_users_total",),
        guidance="Use Google Workspace or Cloud Identity corporate domain accounts.",
    ),
    Control(
        "1.2",
        "Ensure Multi-Factor Authentication (2-Step Verification) is Enforced for All Users",
        _IAM,
        signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled"),
        guidance="Enforce 2-Step Verification in Google Cloud Identity / Workspace.",
    ),
    Control(
        "1.4",
        "Ensure Service Account Keys Are Rotated Every 90 Days or Less",
        _IAM,
        signals=("iam_stale_access_keys",),
        guidance="Rotate user-managed service account keys every 90 days or use Workload Identity.",
    ),
    Control(
        "1.11",
        "Ensure Separation of Duties for Service Account User and Admin Roles",
        _IAM,
        signals=("iam_admin_users",),
        guidance="Do not assign Service Account User and Service Account Admin roles to the same identity.",
    ),
    Control(
        "2.1",
        "Ensure Cloud Storage Bucket Public Access is Blocked (Uniform Bucket-Level Access)",
        _STORAGE,
        signals=("s3_public_access_blocked",),
        guidance="Enforce Uniform Bucket-Level Access and prevent allUsers/allAuthenticatedUsers bindings.",
    ),
    Control(
        "2.2",
        "Ensure Cloud Storage Buckets Employ Customer-Managed Encryption Keys (CMEK)",
        _STORAGE,
        signals=("s3_default_encryption_rate",),
        guidance="Configure Cloud KMS Customer-Managed Encryption Keys on sensitive storage buckets.",
    ),
    Control(
        "2.3",
        "Ensure Cloud KMS Encryption Keys are Rotated Automatically",
        _STORAGE,
        signals=("kms_key_rotation_rate",),
        guidance="Enable automatic rotation on all Cloud KMS CryptoKeys with period <= 90 days.",
    ),
    Control(
        "3.1",
        "Ensure Cloud Audit Logging is Configured Across All Google Cloud Services",
        _LOGGING,
        signals=("cloudtrail_multiregion", "cloudtrail_log_validation"),
        guidance="Enable Admin Activity and Data Access audit logs across all services.",
    ),
    Control(
        "3.3",
        "Ensure Log Sinks are Configured with Retention >= 365 Days",
        _LOGGING,
        signals=("cloudwatch_log_retention_days", "cloudtrail_encrypted"),
        guidance="Configure log sinks to BigQuery or Cloud Storage with minimum 365 days retention.",
    ),
    Control(
        "4.1",
        "Ensure Default Network Does Not Exist in a Project",
        _NETWORK,
        signals=("default_sg_restricted",),
        guidance="Delete the legacy 'default' VPC and configure custom VPC subnets.",
    ),
    Control(
        "4.2",
        "Ensure Legacy Networks Do Not Exist",
        _NETWORK,
        signals=("default_sg_restricted",),
        guidance="Migrate all legacy networks to VPC networks with private Google access.",
    ),
    Control(
        "4.3",
        "Ensure Firewall Rules Do Not Allow Unrestricted Ingress (0.0.0.0/0) on Port 22 (SSH)",
        _NETWORK,
        signals=("open_security_groups",),
        guidance="Restrict firewall rules on port 22 to specific bastion or corporate IP ranges.",
    ),
    Control(
        "4.4",
        "Ensure Firewall Rules Do Not Allow Unrestricted Ingress (0.0.0.0/0) on Port 3389 (RDP)",
        _NETWORK,
        signals=("open_security_groups",),
        guidance="Restrict firewall rules on port 3389 to authorized administrative subnets.",
    ),
    Control(
        "4.8",
        "Ensure VPC Flow Logs are Enabled for Subnets in Virtual Private Cloud",
        _NETWORK,
        signals=("vpc_flow_logs_enabled",),
        guidance="Enable VPC flow logs on all subnets for network traffic visibility.",
    ),
    Control(
        "5.1",
        "Ensure Compute Engine Disks are Encrypted at Rest",
        _COMPUTE,
        signals=("ebs_default_encryption",),
        guidance="Ensure all VM boot and persistent disks are encrypted with CMEK or Google-managed keys.",
    ),
)

FRAMEWORK = Framework(
    id="cis_gcp",
    name="CIS Google Cloud Platform Benchmark",
    version="v3.0",
    description="Center for Internet Security (CIS) GCP Foundations Benchmark — prescriptive Google Cloud hardening checks.",
    controls=CONTROLS,
)

register(FRAMEWORK)

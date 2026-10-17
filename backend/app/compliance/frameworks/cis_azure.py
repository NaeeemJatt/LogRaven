# LogRaven — CIS Microsoft Azure Foundations Benchmark pack
#
# Center for Internet Security (CIS) Azure Foundations Benchmark v2.1

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_IAM = "1 — Identity and Access Management"
_STORAGE = "2 — Storage Accounts"
_DATABASE = "3 — Database Services"
_LOGGING = "4 — Logging and Monitoring"
_NETWORK = "5 — Networking"
_KEYVAULT = "6 — Azure Key Vault"

CONTROLS = (
    Control(
        "1.1",
        "Ensure Multi-Factor Authentication is Enabled for All Privileged Users in Entra ID",
        _IAM,
        signals=("iam_mfa_enforcement_rate", "iam_root_mfa_enabled"),
        guidance="Configure Entra ID Conditional Access policies requiring MFA for all admin roles.",
    ),
    Control(
        "1.3",
        "Ensure Guest Users are Reviewed at Least Every 60 Days",
        _IAM,
        signals=("iam_users_total",),
        guidance="Use Entra ID Access Reviews to audit external guest user accounts.",
    ),
    Control(
        "1.14",
        "Ensure Administrative Roles Have Active PIM (Privileged Identity Management)",
        _IAM,
        signals=("iam_admin_users",),
        guidance="Use Entra ID PIM to enforce just-in-time access for administrative roles.",
    ),
    Control(
        "2.1.1",
        "Ensure Secure Transfer Required (HTTPS) is Enabled for All Storage Accounts",
        _STORAGE,
        signals=("s3_default_encryption_rate",),
        guidance="Require secure transfer (HTTPS) on all storage accounts.",
    ),
    Control(
        "2.1.2",
        "Ensure Blob Public Access is Disabled for Storage Accounts",
        _STORAGE,
        signals=("s3_public_access_blocked",),
        guidance="Set allowBlobPublicAccess to false on all storage accounts.",
    ),
    Control(
        "2.1.5",
        "Ensure Minimum TLS Version of 1.2 is Enforced on Storage Accounts",
        _STORAGE,
        signals=("s3_default_encryption_rate",),
        guidance="Set minimumTlsVersion to TLS1_2 on storage account configuration.",
    ),
    Control(
        "3.1.1",
        "Ensure Transparent Data Encryption (TDE) is Enabled on Azure SQL Databases",
        _DATABASE,
        signals=("rds_encryption_rate",),
        guidance="Enable Transparent Data Encryption (TDE) with customer or service-managed keys.",
    ),
    Control(
        "4.1",
        "Ensure Diagnostic Settings are Configured for Azure Activity Log Export",
        _LOGGING,
        signals=("cloudtrail_multiregion", "cloudtrail_log_validation"),
        guidance="Export Activity Logs to an Azure Monitor Log Analytics workspace or Storage Account.",
    ),
    Control(
        "4.2",
        "Ensure Log Analytics Workspace Data Retention is Greater Than or Equal to 365 Days",
        _LOGGING,
        signals=("cloudwatch_log_retention_days", "cloudtrail_encrypted"),
        guidance="Configure minimum retention period of 365 days in Log Analytics workspace.",
    ),
    Control(
        "5.1.1",
        "Ensure Network Security Group Ingress from 0.0.0.0/0 on Port 22 (SSH) is Denied",
        _NETWORK,
        signals=("open_security_groups",),
        guidance="Remove inbound NSG rules allowing 0.0.0.0/0 or any internet traffic on port 22.",
    ),
    Control(
        "5.1.2",
        "Ensure Network Security Group Ingress from 0.0.0.0/0 on Port 3389 (RDP) is Denied",
        _NETWORK,
        signals=("open_security_groups",),
        guidance="Remove inbound NSG rules allowing 0.0.0.0/0 on port 3389.",
    ),
    Control(
        "5.2",
        "Ensure Virtual Network Flow Logs (Network Watcher) are Configured",
        _NETWORK,
        signals=("vpc_flow_logs_enabled",),
        guidance="Enable NSG flow logs and Network Watcher in all active regions.",
    ),
    Control(
        "6.1",
        "Ensure Auto-Rotation Policy is Enabled for Keys in Azure Key Vault",
        _KEYVAULT,
        signals=("kms_key_rotation_rate",),
        guidance="Configure automated key rotation policy on Azure Key Vault keys with interval <= 1 year.",
    ),
)

FRAMEWORK = Framework(
    id="cis_azure",
    name="CIS Microsoft Azure Benchmark",
    version="v2.1",
    description="Center for Internet Security (CIS) Azure Foundations Benchmark — prescriptive Microsoft Azure hardening checks.",
    controls=CONTROLS,
)

register(FRAMEWORK)

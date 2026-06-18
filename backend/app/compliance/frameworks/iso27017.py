# LogRaven — ISO/IEC 27017 (cloud security) framework pack
#
# Cloud-specific guidance extending ISO 27002. Subset substantiated by AWS evidence.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_CLOUD = "Cloud Service Controls"

CONTROLS = (
    Control("CLD.6.3.1", "Shared roles and responsibilities within a cloud environment", _CLOUD,
            automatable=False,
            guidance="Document the shared-responsibility split between provider and customer."),
    Control("CLD.9.5.1", "Segregation in virtual computing environments", _CLOUD,
            signals=("default_sg_restricted", "open_security_groups", "vpc_flow_logs_enabled"),
            guidance="Segregate tenant/workload networks; restrict and monitor traffic."),
    Control("CLD.9.5.2", "Virtual machine hardening", _CLOUD,
            signals=("config_recorder_enabled", "ebs_default_encryption", "inspector_enabled"),
            guidance="Harden and scan virtual machines; encrypt volumes."),
    Control("CLD.12.1.5", "Administrator's operational security", _CLOUD,
            signals=("iam_admin_users", "iam_mfa_enforcement_rate", "iam_root_mfa_enabled"),
            guidance="Protect administrative operations with MFA and least privilege."),
    Control("CLD.12.4.5", "Monitoring of cloud services", _CLOUD,
            signals=("cloudtrail_multiregion", "guardduty_enabled", "security_alarms_configured"),
            guidance="Monitor cloud service usage and security events."),
    Control("CLD.10.1.1", "Encryption of customer data in the cloud", _CLOUD,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "kms_key_rotation_rate"),
            guidance="Encrypt customer data and manage keys in the cloud."),
    Control("CLD.8.1.5", "Removal of cloud service customer assets", _CLOUD,
            signals=("iam_stale_access_keys", "s3_public_access_blocked"),
            guidance="Securely remove and de-provision assets and credentials."),
)

FRAMEWORK = Framework(
    id="iso27017",
    name="ISO/IEC 27017",
    version="2015",
    description="Cloud-specific information security controls extending ISO/IEC 27002.",
    controls=CONTROLS,
)

register(FRAMEWORK)

# LogRaven — ISO/IEC 27018 (protection of PII in public clouds) framework pack
#
# Privacy controls for processors of personally identifiable information (PII)
# in public clouds. Subset substantiated by AWS evidence.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_PII = "PII Protection in Public Clouds"

CONTROLS = (
    Control("A.10.1", "Cryptographic protection of PII", _PII,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption", "kms_key_rotation_rate"),
            guidance="Encrypt PII at rest and in transit; manage and rotate keys."),
    Control("A.11.2", "Access to PII restricted and logged", _PII,
            signals=("iam_admin_users", "access_analyzer_external_findings", "cloudtrail_multiregion"),
            guidance="Restrict and log all access to PII."),
    Control("A.12.1", "Protection of data on storage media leaving premises", _PII,
            signals=("ebs_default_encryption", "s3_default_encryption_rate"),
            guidance="Encrypt storage media so off-premise data is protected."),
    Control("A.9.4", "Secure log-on and authentication for PII access", _PII,
            signals=("iam_mfa_enforcement_rate", "iam_password_policy_exists"),
            guidance="Require strong authentication and MFA for PII access."),
    Control("A.16.1", "PII breach detection and response", _PII,
            signals=("guardduty_enabled", "guardduty_high_severity_findings", "security_alarms_configured"),
            guidance="Detect and respond to events that may expose PII."),
    Control("A.12.3", "Backup and recovery of PII", _PII,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Back up PII to enable recovery while preserving confidentiality."),
    Control("A.18.1", "Public-exposure prevention for PII stores", _PII,
            signals=("s3_public_access_blocked", "open_security_groups"),
            guidance="Prevent public exposure of PII data stores."),
)

FRAMEWORK = Framework(
    id="iso27018",
    name="ISO/IEC 27018",
    version="2019",
    description="Code of practice for protection of PII in public clouds acting as PII processors.",
    controls=CONTROLS,
)

register(FRAMEWORK)

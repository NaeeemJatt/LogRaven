# LogRaven — GDPR (Article 32 security of processing) framework pack
#
# GDPR is largely organizational/legal; this pack covers the technical security
# measures of Article 32 plus closely related obligations. Non-technical
# articles are marked automatable=False.

from __future__ import annotations

from app.compliance.frameworks.base import Control, Framework, register

_SEC = "Art. 32 — Security of Processing"
_GOV = "Governance & Accountability"

CONTROLS = (
    Control("Art.32(1)(a)", "Pseudonymisation and encryption of personal data", _SEC,
            signals=("s3_default_encryption_rate", "rds_encryption_rate", "ebs_default_encryption", "kms_key_rotation_rate"),
            guidance="Encrypt personal data at rest across all stores and rotate keys."),
    Control("Art.32(1)(b)", "Confidentiality, integrity, availability and resilience", _SEC,
            signals=("s3_public_access_blocked", "open_security_groups", "backup_configured"),
            guidance="Ensure confidentiality and resilience: block public access, restrict ports, back up data."),
    Control("Art.32(1)(c)", "Ability to restore availability and access after an incident", _SEC,
            signals=("backup_configured", "rds_backups_enabled"),
            guidance="Maintain tested backups enabling timely restoration."),
    Control("Art.32(1)(d)", "Process for regularly testing and evaluating security", _SEC,
            signals=("config_recorder_enabled", "securityhub_enabled", "inspector_enabled"),
            guidance="Continuously test security posture (Config, Security Hub, Inspector)."),
    Control("Art.32(2)", "Account for risks from accidental or unlawful access", _SEC,
            signals=("guardduty_enabled", "access_analyzer_external_findings", "vpc_flow_logs_enabled"),
            guidance="Detect unlawful access via GuardDuty/Access Analyzer/flow logs."),
    Control("Art.25", "Data protection by design and by default", _GOV,
            signals=("s3_public_access_blocked", "default_sg_restricted"),
            guidance="Default to least exposure: block public access and restrict default SGs."),
    Control("Art.5(1)(f)", "Integrity and confidentiality principle", _GOV,
            signals=("iam_mfa_enforcement_rate", "cloudtrail_multiregion"),
            guidance="Protect personal data with access controls and audit logging."),
    Control("Art.30", "Records of processing activities", _GOV, automatable=False,
            guidance="Maintain records of processing activities (RoPA)."),
    Control("Art.33", "Notification of a personal data breach to supervisory authority", _GOV,
            automatable=False,
            guidance="Define a 72-hour breach notification process."),
)

FRAMEWORK = Framework(
    id="gdpr",
    name="GDPR",
    version="Regulation (EU) 2016/679",
    description="EU General Data Protection Regulation — technical security measures (Art. 32) and related obligations.",
    controls=CONTROLS,
)

register(FRAMEWORK)

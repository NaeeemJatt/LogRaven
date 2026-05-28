# LogRaven — SOC 2 Compliance Schemas and PII Validation

from __future__ import annotations

import json
import os
import re
from typing import Any, TypedDict

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Patterns that must never appear in sanitized AI-bound output
_ARN_PATTERN = re.compile(r"arn:aws:[a-z0-9-]+:[a-z0-9-]*:\d{12}:", re.IGNORECASE)
_IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_ACCOUNT_ID_PATTERN = re.compile(r"\b\d{12}\b")
_ACCESS_KEY_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")


class CloudtrailSanitized(TypedDict):
    total_events_reviewed: int
    audit_period_days: int
    login_events: int
    failed_login_attempts: int
    mfa_used_on_logins: int
    privilege_escalation_events: int
    policy_change_events: int
    resource_creation_events: int
    resource_deletion_events: int
    access_key_creation_events: int
    off_hours_events: int
    unique_source_ip_count: int
    cross_region_events: int


class IamSanitized(TypedDict):
    total_users: int
    mfa_enabled_count: int
    mfa_disabled_count: int
    mfa_enforcement_rate_percent: float
    password_policy_exists: bool
    password_min_length: int | None
    password_requires_symbols: bool | None
    password_requires_numbers: bool | None
    password_max_age_days: int | None
    root_mfa_enabled: bool


class GuarddutySanitized(TypedDict):
    enabled: bool
    total_findings: int
    high_severity_findings: int
    finding_categories: list[str]


class SanitizedEvidence(TypedDict):
    cloudtrail: CloudtrailSanitized
    iam: IamSanitized
    guardduty: GuarddutySanitized


def _scan_text_for_pii(text: str) -> list[str]:
    violations: list[str] = []
    if _ARN_PATTERN.search(text):
        violations.append("ARN")
    if _IPV4_PATTERN.search(text):
        violations.append("IP address")
    if _ACCESS_KEY_PATTERN.search(text):
        violations.append("access key ID")
    if _ACCOUNT_ID_PATTERN.search(text):
        violations.append("12-digit account ID")
    return violations


def validate_no_pii(sanitized: dict[str, Any], *, strict: bool | None = None) -> None:
    """
    Ensure sanitized evidence contains no ARNs, IPs, account IDs, or access keys.

    Raises ValueError in strict mode (tests/dev). Logs a warning in production.
    """
    if strict is None:
        strict = os.getenv("DEBUG", "").lower() in ("true", "1") or os.getenv("PYTEST_CURRENT_TEST") is not None

    text = json.dumps(sanitized, default=str)
    violations = _scan_text_for_pii(text)
    if not violations:
        return

    message = f"Sanitized output contains forbidden PII patterns: {', '.join(sorted(set(violations)))}"
    if strict:
        raise ValueError(message)
    logger.warning(message)

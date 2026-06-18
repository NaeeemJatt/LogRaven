# LogRaven — SOC 2 Evidence Sanitizer
#
# Converts raw AWS collector output into aggregate statistics safe for external AI.
# No ARNs, account IDs, IP addresses, usernames, or access keys in output.

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any

from app.compliance.cloudtrail_utils import (
    classify_event,
    get_aws_region,
    get_source_ip,
    is_failed_login,
    is_mfa_login,
    parse_event_time,
)
from app.compliance.constants import (
    OFF_HOURS_UTC_END,
    OFF_HOURS_UTC_START,
    RESOURCE_CREATION_EVENTS,
    RESOURCE_DELETION_EVENTS,
)
from app.compliance.schemas import validate_no_pii
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _classify_event(event_name: str) -> str:
    return classify_event(event_name)


def _count_failed_logins(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if is_failed_login(event))


def _count_mfa_on_logins(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if is_mfa_login(event))


def _count_off_hours(events: list[dict[str, Any]]) -> int:
    count = 0
    for event in events:
        event_time = parse_event_time(event)
        if event_time is None:
            continue
        hour = event_time.astimezone(timezone.utc).hour
        if hour < OFF_HOURS_UTC_START or hour >= OFF_HOURS_UTC_END:
            count += 1
    return count


def _unique_source_ip_count(events: list[dict[str, Any]]) -> int:
    ips = {ip for event in events if (ip := get_source_ip(event))}
    return len(ips)


def _cross_region_events(events: list[dict[str, Any]]) -> int:
    regions = [region for event in events if (region := get_aws_region(event))]
    if not regions:
        return 0
    primary_region = Counter(regions).most_common(1)[0][0]
    return sum(1 for region in regions if region != primary_region)


def _audit_period_days(cloudtrail_events: dict[str, Any]) -> int:
    date_range = cloudtrail_events.get("date_range") or {}
    start_raw = date_range.get("start")
    end_raw = date_range.get("end")
    if not start_raw or not end_raw:
        return 0
    try:
        start = date.fromisoformat(str(start_raw))
        end = date.fromisoformat(str(end_raw))
        return max((end - start).days + 1, 0)
    except ValueError:
        return 0


def _sanitize_cloudtrail(cloudtrail_events: dict[str, Any]) -> dict[str, Any]:
    events = cloudtrail_events.get("events") or []
    login_events = 0
    privilege_events = 0
    policy_events = 0
    resource_creation = 0
    resource_deletion = 0
    access_key_creation = 0

    for event in events:
        name = event.get("EventName") or ""
        category = _classify_event(name)
        if category == "login":
            login_events += 1
        elif category == "privilege":
            privilege_events += 1
        elif category == "policy":
            policy_events += 1
        elif name in RESOURCE_CREATION_EVENTS:
            resource_creation += 1
        elif name in RESOURCE_DELETION_EVENTS:
            resource_deletion += 1
        elif category == "access_key" and name == "CreateAccessKey":
            access_key_creation += 1

    return {
        "total_events_reviewed": int(cloudtrail_events.get("total_count") or len(events)),
        "audit_period_days": _audit_period_days(cloudtrail_events),
        "login_events": login_events,
        "failed_login_attempts": _count_failed_logins(events),
        "mfa_used_on_logins": _count_mfa_on_logins(events),
        "privilege_escalation_events": privilege_events,
        "policy_change_events": policy_events,
        "resource_creation_events": resource_creation,
        "resource_deletion_events": resource_deletion,
        "access_key_creation_events": access_key_creation,
        "off_hours_events": _count_off_hours(events),
        "unique_source_ip_count": _unique_source_ip_count(events),
        "cross_region_events": _cross_region_events(events),
    }


def _sanitize_iam(iam_summary: dict[str, Any]) -> dict[str, Any]:
    mfa_enabled = int(iam_summary.get("mfa_enabled_count") or 0)
    mfa_disabled = int(iam_summary.get("mfa_disabled_count") or 0)
    mfa_total = mfa_enabled + mfa_disabled
    enforcement_rate = (mfa_enabled / mfa_total * 100.0) if mfa_total else 0.0

    password_policy = iam_summary.get("password_policy") or {}
    password_exists = bool(iam_summary.get("password_policy_exists"))

    return {
        "total_users": int(iam_summary.get("user_count") or 0),
        "mfa_enabled_count": mfa_enabled,
        "mfa_disabled_count": mfa_disabled,
        "mfa_enforcement_rate_percent": round(enforcement_rate, 2),
        "password_policy_exists": password_exists,
        "password_min_length": password_policy.get("MinimumPasswordLength") if password_exists else None,
        "password_requires_symbols": password_policy.get("RequireSymbols") if password_exists else None,
        "password_requires_numbers": password_policy.get("RequireNumbers") if password_exists else None,
        "password_max_age_days": password_policy.get("MaxPasswordAge") if password_exists else None,
        "root_mfa_enabled": bool(iam_summary.get("has_root_mfa")),
    }


def _sanitize_guardduty(guardduty_findings: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": bool(guardduty_findings.get("enabled")),
        "total_findings": int(guardduty_findings.get("finding_count") or 0),
        "high_severity_findings": int(guardduty_findings.get("high_severity_count") or 0),
        "finding_categories": list(guardduty_findings.get("finding_types") or []),
    }


def sanitize_for_ai(
    cloudtrail_events: dict[str, Any],
    iam_summary: dict[str, Any],
    guardduty_findings: dict[str, Any],
    extended: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convert raw AWS collector output into a PII-free summary safe for the AI engine.

    `extended` carries the deep-collector sections (iam_extended, cloudtrail_config,
    encryption, network, monitoring, backup), which are already aggregate/PII-free;
    they are merged in and re-validated for defense in depth.

    Raises ValueError if the output still contains forbidden PII patterns (strict mode).
    """
    sanitized = {
        "cloudtrail": _sanitize_cloudtrail(cloudtrail_events),
        "iam": _sanitize_iam(iam_summary),
        "guardduty": _sanitize_guardduty(guardduty_findings),
    }
    if extended:
        # Deep-collector sections are aggregate-only; pass through under their keys.
        for key in ("iam_extended", "cloudtrail_config", "encryption", "network", "monitoring", "backup"):
            if key in extended and extended[key] is not None:
                sanitized[key] = extended[key]
    validate_no_pii(sanitized)
    logger.info(
        "Sanitized evidence: %d cloudtrail events, %d IAM users, guardduty_enabled=%s",
        sanitized["cloudtrail"]["total_events_reviewed"],
        sanitized["iam"]["total_users"],
        sanitized["guardduty"]["enabled"],
    )
    return sanitized


if __name__ == "__main__":
    sample_cloudtrail = {
        "total_count": 2,
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "events": [
            {
                "EventTime": "2026-01-15T03:00:00+00:00",
                "EventName": "ConsoleLogin",
                "CloudTrailEvent": {
                    "sourceIPAddress": "203.0.113.10",
                    "awsRegion": "us-east-1",
                    "additionalEventData": {"MFAUsed": "Yes"},
                },
            },
            {
                "EventTime": "2026-01-16T10:00:00+00:00",
                "EventName": "AssumeRole",
                "CloudTrailEvent": {
                    "sourceIPAddress": "198.51.100.5",
                    "awsRegion": "us-west-2",
                },
            },
        ],
    }
    sample_iam = {
        "user_count": 10,
        "mfa_enabled_count": 8,
        "mfa_disabled_count": 2,
        "password_policy_exists": True,
        "password_policy": {
            "MinimumPasswordLength": 14,
            "RequireSymbols": True,
            "RequireNumbers": True,
            "MaxPasswordAge": 90,
        },
        "has_root_mfa": True,
    }
    sample_guardduty = {
        "enabled": True,
        "finding_count": 1,
        "high_severity_count": 1,
        "finding_types": ["UnauthorizedAPICall"],
    }
    import json

    print(json.dumps(sanitize_for_ai(sample_cloudtrail, sample_iam, sample_guardduty), indent=2))

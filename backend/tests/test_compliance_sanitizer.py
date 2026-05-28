"""Tests for SOC 2 evidence sanitizer."""

import json

import pytest

from app.compliance.schemas import validate_no_pii
from app.compliance.sanitizer import sanitize_for_ai


@pytest.fixture
def raw_cloudtrail_with_pii() -> dict:
    return {
        "total_count": 4,
        "date_range": {"start": "2026-01-01", "end": "2026-01-07"},
        "events": [
            {
                "EventTime": "2026-01-02T03:30:00+00:00",
                "EventName": "ConsoleLogin",
                "Username": "alice@company.com",
                "Resources": [{"ARN": "arn:aws:iam::123456789012:user/alice"}],
                "CloudTrailEvent": {
                    "sourceIPAddress": "203.0.113.10",
                    "awsRegion": "us-east-1",
                    "errorCode": "Failed authentication",
                },
            },
            {
                "EventTime": "2026-01-03T14:00:00+00:00",
                "EventName": "ConsoleLogin",
                "CloudTrailEvent": {
                    "sourceIPAddress": "203.0.113.10",
                    "awsRegion": "us-east-1",
                    "additionalEventData": {"MFAUsed": "Yes"},
                },
            },
            {
                "EventTime": "2026-01-04T15:00:00+00:00",
                "EventName": "AssumeRole",
                "CloudTrailEvent": {
                    "sourceIPAddress": "198.51.100.5",
                    "awsRegion": "us-west-2",
                },
            },
            {
                "EventTime": "2026-01-05T16:00:00+00:00",
                "EventName": "CreateAccessKey",
                "CloudTrailEvent": {
                    "sourceIPAddress": "198.51.100.5",
                    "awsRegion": "us-east-1",
                },
            },
        ],
    }


@pytest.fixture
def raw_iam_summary() -> dict:
    return {
        "user_count": 5,
        "mfa_enabled_count": 3,
        "mfa_disabled_count": 2,
        "password_policy_exists": True,
        "password_policy": {
            "MinimumPasswordLength": 12,
            "RequireSymbols": True,
            "RequireNumbers": True,
            "MaxPasswordAge": 90,
        },
        "has_root_mfa": False,
    }


@pytest.fixture
def raw_guardduty() -> dict:
    return {
        "enabled": True,
        "finding_count": 2,
        "high_severity_count": 2,
        "finding_types": ["Recon:EC2/PortProbeUnprotectedPort", "UnauthorizedAPICall"],
    }


def test_sanitize_for_ai_structure(
    raw_cloudtrail_with_pii,
    raw_iam_summary,
    raw_guardduty,
):
    result = sanitize_for_ai(raw_cloudtrail_with_pii, raw_iam_summary, raw_guardduty)

    assert set(result.keys()) == {"cloudtrail", "iam", "guardduty"}

    cloudtrail = result["cloudtrail"]
    assert cloudtrail["total_events_reviewed"] == 4
    assert cloudtrail["audit_period_days"] == 7
    assert cloudtrail["login_events"] == 2
    assert cloudtrail["failed_login_attempts"] == 1
    assert cloudtrail["mfa_used_on_logins"] == 1
    assert cloudtrail["privilege_escalation_events"] == 1
    assert cloudtrail["access_key_creation_events"] == 1
    assert cloudtrail["off_hours_events"] == 1
    assert cloudtrail["unique_source_ip_count"] == 2
    assert cloudtrail["cross_region_events"] == 1

    iam = result["iam"]
    assert iam["total_users"] == 5
    assert iam["mfa_enforcement_rate_percent"] == 60.0
    assert iam["password_min_length"] == 12
    assert iam["password_requires_symbols"] is True
    assert iam["root_mfa_enabled"] is False

    guardduty = result["guardduty"]
    assert guardduty["enabled"] is True
    assert guardduty["total_findings"] == 2
    assert guardduty["high_severity_findings"] == 2
    assert len(guardduty["finding_categories"]) == 2


def test_sanitize_for_ai_contains_no_pii(
    raw_cloudtrail_with_pii,
    raw_iam_summary,
    raw_guardduty,
):
    result = sanitize_for_ai(raw_cloudtrail_with_pii, raw_iam_summary, raw_guardduty)
    text = json.dumps(result)

    assert "203.0.113.10" not in text
    assert "alice@company.com" not in text
    assert "arn:aws" not in text
    assert "123456789012" not in text
    validate_no_pii(result, strict=True)


def test_mfa_enforcement_rate_zero_when_no_users():
    result = sanitize_for_ai(
        {"events": [], "total_count": 0, "date_range": {"start": "2026-01-01", "end": "2026-01-01"}},
        {
            "user_count": 0,
            "mfa_enabled_count": 0,
            "mfa_disabled_count": 0,
            "password_policy_exists": False,
            "password_policy": None,
            "has_root_mfa": False,
        },
        {"enabled": False, "finding_count": 0, "high_severity_count": 0, "finding_types": []},
    )
    assert result["iam"]["mfa_enforcement_rate_percent"] == 0.0

# LogRaven — CloudTrail Event Parsing Utilities
#
# Shared by aws_collector (raw storage) and sanitizer (aggregate stats only).

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.compliance.constants import EVENT_NAME_TO_CATEGORY


def get_cloudtrail_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Return parsed CloudTrailEvent JSON from a trimmed collector event."""
    payload = event.get("CloudTrailEvent")
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}


def parse_event_time(event: dict[str, Any]) -> datetime | None:
    """Parse EventTime from a collector event record."""
    raw_time = event.get("EventTime")
    if isinstance(raw_time, datetime):
        return raw_time if raw_time.tzinfo else raw_time.replace(tzinfo=timezone.utc)
    if isinstance(raw_time, str):
        try:
            dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def get_source_ip(event: dict[str, Any]) -> str | None:
    payload = get_cloudtrail_payload(event)
    ip = payload.get("sourceIPAddress")
    return str(ip) if ip else None


def get_aws_region(event: dict[str, Any]) -> str | None:
    payload = get_cloudtrail_payload(event)
    region = payload.get("awsRegion")
    return str(region) if region else None


def is_failed_login(event: dict[str, Any]) -> bool:
    if event.get("EventName") != "ConsoleLogin":
        return False
    payload = get_cloudtrail_payload(event)
    return bool(payload.get("errorCode"))


def is_mfa_login(event: dict[str, Any]) -> bool:
    if event.get("EventName") != "ConsoleLogin":
        return False
    payload = get_cloudtrail_payload(event)
    additional = payload.get("additionalEventData") or {}
    return additional.get("MFAUsed") == "Yes"


def classify_event(event_name: str) -> str:
    """Map CloudTrail event name to sanitizer category."""
    return EVENT_NAME_TO_CATEGORY.get(event_name, "other")


def trim_cloudtrail_event(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a LookupEvents record for raw DB storage (may contain PII)."""
    event: dict[str, Any] = {
        "EventTime": raw["EventTime"].isoformat() if raw.get("EventTime") else None,
        "EventName": raw.get("EventName"),
        "EventSource": raw.get("EventSource"),
        "Username": raw.get("Username"),
        "Resources": raw.get("Resources", []),
    }
    cloud_trail_event = raw.get("CloudTrailEvent")
    if cloud_trail_event:
        try:
            event["CloudTrailEvent"] = json.loads(cloud_trail_event)
        except (json.JSONDecodeError, TypeError):
            event["CloudTrailEvent"] = cloud_trail_event
    return event

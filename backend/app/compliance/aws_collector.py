# LogRaven — SOC 2 AWS Evidence Collector
#
# Connects to a customer AWS account via STS AssumeRole (read-only role ARN).
# Temporary credentials are held in memory only — never persisted.
#
# PRIVACY BOUNDARY: Raw collector output (Usernames, ARNs, IPs) is stored in
# PostgreSQL only. The sanitizer strips all PII before any external AI call.
#
# LogRaven's runtime must have its own AWS identity (env vars or instance role)
# with permission to sts:AssumeRole on the customer role.
#
# CUSTOMER IAM POLICY TEMPLATE (attach to the role they create for LogRaven):
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Action": [
#         "cloudtrail:LookupEvents",
#         "iam:GetAccountSummary",
#         "iam:GetAccountPasswordPolicy",
#         "iam:ListUsers",
#         "iam:ListMFADevices",
#         "guardduty:ListDetectors",
#         "guardduty:ListFindings",
#         "guardduty:GetFindings"
#       ],
#       "Resource": "*"
#     }
#   ]
# }

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.compliance.cloudtrail_utils import trim_cloudtrail_event
from app.compliance.constants import CLOUDTRAIL_EVENT_NAMES
from app.utils.logger import get_logger

logger = get_logger(__name__)

SESSION_NAME = "LogRavenAudit"
SESSION_DURATION_SECONDS = 3600
MAX_CLOUDTRAIL_EVENTS = 1000
MAX_IAM_USERS = 100
MAX_GUARDDUTY_FINDINGS = 50
GUARDDUTY_MIN_SEVERITY = 4.0
DEFAULT_REGION = "us-east-1"


class AWSConnectionError(Exception):
    """Raised when STS AssumeRole fails or a session cannot be established."""


def _resolve_region(session: boto3.Session, region: str | None = None) -> str:
    return region or session.region_name or DEFAULT_REGION


def get_aws_session(role_arn: str) -> boto3.Session:
    """
    Assume the customer read-only role and return a boto3 Session with temporary credentials.

    Credentials exist in memory only for the session lifetime (max 1 hour).
    """
    try:
        sts = boto3.client("sts")
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=SESSION_NAME,
            DurationSeconds=SESSION_DURATION_SECONDS,
        )
        creds = response["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        message = exc.response.get("Error", {}).get("Message", str(exc))
        logger.error("STS AssumeRole failed for %s: %s — %s", role_arn, code, message)
        raise AWSConnectionError(f"Failed to assume role {role_arn}: {code} — {message}") from exc
    except BotoCoreError as exc:
        logger.error("STS AssumeRole failed for %s: %s", role_arn, exc)
        raise AWSConnectionError(f"Failed to assume role {role_arn}: {exc}") from exc


def _date_range_dict(start_date: date, end_date: date) -> dict[str, str]:
    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
    }


def _cloudtrail_window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    return start_dt, end_dt


def _fetch_events_for_name(
    client: Any,
    event_name: str,
    start_dt: datetime,
    end_dt: datetime,
    remaining: int,
) -> list[dict[str, Any]]:
    """Fetch CloudTrail events for a single EventName, up to remaining cap."""
    events: list[dict[str, Any]] = []
    next_token: str | None = None

    while len(events) < remaining:
        params: dict[str, Any] = {
            "LookupAttributes": [{"AttributeKey": "EventName", "AttributeValue": event_name}],
            "StartTime": start_dt,
            "EndTime": end_dt,
            "MaxResults": min(50, remaining - len(events)),
        }
        if next_token:
            params["NextToken"] = next_token

        response = client.lookup_events(**params)
        for raw in response.get("Events", []):
            events.append(trim_cloudtrail_event(raw))
            if len(events) >= remaining:
                break

        next_token = response.get("NextToken")
        if not next_token:
            break

    return events


def get_cloudtrail_events(
    session: boto3.Session,
    start_date: date,
    end_date: date,
    region: str | None = None,
) -> dict[str, Any]:
    """
    Pull CloudTrail LookupEvents for the date range, filtered to SOC-relevant event names.

    Uses per-event-name API queries for efficiency. Returns up to 1000 events.
    """
    date_range = _date_range_dict(start_date, end_date)
    empty = {"events": [], "total_count": 0, "date_range": date_range}

    try:
        client = session.client("cloudtrail", region_name=_resolve_region(session, region))
        start_dt, end_dt = _cloudtrail_window(start_date, end_date)
        events: list[dict[str, Any]] = []

        for event_name in sorted(CLOUDTRAIL_EVENT_NAMES):
            if len(events) >= MAX_CLOUDTRAIL_EVENTS:
                break
            remaining = MAX_CLOUDTRAIL_EVENTS - len(events)
            batch = _fetch_events_for_name(client, event_name, start_dt, end_dt, remaining)
            events.extend(batch)

        logger.info(
            "CloudTrail collection complete: %d events (%s to %s)",
            len(events),
            start_date,
            end_date,
        )
        return {"events": events, "total_count": len(events), "date_range": date_range}

    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        logger.warning("CloudTrail LookupEvents failed: %s", code)
        return empty
    except BotoCoreError as exc:
        logger.warning("CloudTrail LookupEvents failed: %s", exc)
        return empty


def get_iam_summary(session: boto3.Session, region: str | None = None) -> dict[str, Any]:
    """
    Collect IAM account summary: user counts, MFA coverage, password policy, root MFA status.
    """
    result: dict[str, Any] = {
        "user_count": 0,
        "mfa_enabled_count": 0,
        "mfa_disabled_count": 0,
        "password_policy_exists": False,
        "password_policy": None,
        "has_root_mfa": False,
    }

    try:
        iam = session.client("iam", region_name=_resolve_region(session, region))

        try:
            summary = iam.get_account_summary().get("SummaryMap", {})
            result["user_count"] = int(summary.get("Users", 0))
            result["has_root_mfa"] = summary.get("AccountMFAEnabled", 0) == 1
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            logger.warning("IAM GetAccountSummary failed: %s", code)

        try:
            policy = iam.get_account_password_policy()
            result["password_policy_exists"] = True
            result["password_policy"] = policy.get("PasswordPolicy")
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            if code == "NoSuchEntity":
                result["password_policy_exists"] = False
                result["password_policy"] = None
            else:
                logger.warning("IAM GetAccountPasswordPolicy failed: %s", code)

        mfa_enabled = 0
        mfa_disabled = 0
        users_seen = 0
        paginator = iam.get_paginator("list_users")
        for page in paginator.paginate(PaginationConfig={"MaxItems": MAX_IAM_USERS}):
            for user in page.get("Users", []):
                if users_seen >= MAX_IAM_USERS:
                    break
                users_seen += 1
                username = user["UserName"]
                try:
                    mfa_response = iam.list_mfa_devices(UserName=username)
                    if mfa_response.get("MFADevices"):
                        mfa_enabled += 1
                    else:
                        mfa_disabled += 1
                except ClientError as exc:
                    code = exc.response.get("Error", {}).get("Code", "Unknown")
                    logger.warning("IAM ListMFADevices failed for user #%d: %s", users_seen, code)
                    mfa_disabled += 1
            if users_seen >= MAX_IAM_USERS:
                break

        result["mfa_enabled_count"] = mfa_enabled
        result["mfa_disabled_count"] = mfa_disabled
        if users_seen > 0:
            result["user_count"] = max(result["user_count"], users_seen)

        logger.info(
            "IAM summary: %d users, MFA enabled=%d disabled=%d, root_mfa=%s",
            result["user_count"],
            mfa_enabled,
            mfa_disabled,
            result["has_root_mfa"],
        )
        return result

    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        logger.warning("IAM summary collection failed: %s", code)
        return result
    except BotoCoreError as exc:
        logger.warning("IAM summary collection failed: %s", exc)
        return result


def get_guardduty_findings(
    session: boto3.Session,
    region: str | None = None,
) -> dict[str, Any]:
    """
    List GuardDuty findings with severity >= 4.0 (max 50).
    """
    empty: dict[str, Any] = {
        "enabled": False,
        "finding_count": 0,
        "high_severity_count": 0,
        "finding_types": [],
    }

    resolved_region = _resolve_region(session, region)

    try:
        client = session.client("guardduty", region_name=resolved_region)
        detectors = client.list_detectors().get("DetectorIds", [])
        if not detectors:
            logger.info("GuardDuty not enabled in region %s", resolved_region)
            return empty

        detector_id = detectors[0]
        finding_ids: list[str] = []
        next_token: str | None = None

        while len(finding_ids) < MAX_GUARDDUTY_FINDINGS:
            params: dict[str, Any] = {
                "DetectorId": detector_id,
                "FindingCriteria": {
                    "Criterion": {
                        "severity": {
                            "Gte": GUARDDUTY_MIN_SEVERITY,
                        },
                    },
                },
                "MaxResults": min(50, MAX_GUARDDUTY_FINDINGS - len(finding_ids)),
            }
            if next_token:
                params["NextToken"] = next_token

            response = client.list_findings(**params)
            finding_ids.extend(response.get("FindingIds", []))
            next_token = response.get("NextToken")
            if not next_token or len(finding_ids) >= MAX_GUARDDUTY_FINDINGS:
                break

        finding_ids = finding_ids[:MAX_GUARDDUTY_FINDINGS]
        if not finding_ids:
            logger.info("GuardDuty enabled in %s but no high-severity findings", resolved_region)
            return {
                "enabled": True,
                "finding_count": 0,
                "high_severity_count": 0,
                "finding_types": [],
            }

        findings_response = client.get_findings(DetectorId=detector_id, FindingIds=finding_ids)
        findings = findings_response.get("Findings", [])
        finding_types = sorted({f.get("Type", "") for f in findings if f.get("Type")})
        high_severity_count = sum(
            1 for f in findings if float(f.get("Severity", 0)) >= GUARDDUTY_MIN_SEVERITY
        )

        logger.info(
            "GuardDuty: %d findings (>=%.1f severity), types=%d",
            len(findings),
            GUARDDUTY_MIN_SEVERITY,
            len(finding_types),
        )
        return {
            "enabled": True,
            "finding_count": len(findings),
            "high_severity_count": high_severity_count,
            "finding_types": finding_types,
        }

    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        logger.warning("GuardDuty collection failed in %s: %s", resolved_region, code)
        return empty
    except BotoCoreError as exc:
        logger.warning("GuardDuty collection failed in %s: %s", resolved_region, exc)
        return empty

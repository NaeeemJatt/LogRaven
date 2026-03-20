# LogRaven — AWS CloudTrail Parser

import json
from datetime import datetime, timezone

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent, normalize_entity
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SENSITIVE_ACTIONS = {
    "CreateAccessKey", "DeleteAccessKey",
    "AttachUserPolicy", "AttachRolePolicy",
    "CreateUser", "DeleteUser",
    "AuthorizeSecurityGroupIngress", "ModifyInstanceAttribute",
    "PutBucketPolicy", "GetSecretValue", "AssumeRole",
}


class CloudTrailParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                raw = json.load(fh)
        except Exception as e:
            logger.error("Failed to load CloudTrail JSON %s: %s", file_path, e)
            return []

        # Handle both {"Records": [...]} and a single event dict
        if isinstance(raw, dict) and "Records" in raw:
            records = raw["Records"]
        elif isinstance(raw, dict):
            records = [raw]
        elif isinstance(raw, list):
            records = raw
        else:
            logger.warning("Unrecognised CloudTrail structure in %s", file_path)
            return []

        events: list[NormalizedEvent] = []
        for rec in records:
            event = self._parse_record(rec)
            if event:
                events.append(event)
        return events

    def _parse_record(self, rec: dict) -> NormalizedEvent | None:
        try:
            event_time_raw = rec.get("eventTime", "")
            ts = self._safe_parse_timestamp(event_time_raw.replace("Z", "").split(".")[0]) if event_time_raw else None
            if ts is None:
                ts = datetime.now(timezone.utc).replace(tzinfo=None)

            event_source = rec.get("eventSource", "")
            event_name   = rec.get("eventName", "")
            source_ip    = rec.get("sourceIPAddress", None)
            error_code   = rec.get("errorCode", None)

            # Extract username from userIdentity
            identity = rec.get("userIdentity", {}) or {}
            username = (
                identity.get("userName")
                or identity.get("arn")
                or identity.get("type")
                or None
            )

            event_type = "auth_failure" if error_code else "api_call"

            flags: list[str] = []
            if error_code:
                flags.append("failed_api_call")
            if event_name in _SENSITIVE_ACTIONS:
                flags.append("sensitive_action")

            raw_msg = json.dumps(rec)[:500]

            # Populate extra_fields for YAML rule matching
            extra: dict = {"eventSource": event_source or "", "eventName": event_name or ""}
            if error_code:
                extra["errorCode"] = str(error_code)
            for field_name in ("errorMessage", "userAgent", "awsRegion", "requestRegion"):
                val = rec.get(field_name)
                if val:
                    extra[field_name] = str(val)[:200]
            # Flatten top-level requestParameters (strings/numbers only)
            req_params = rec.get("requestParameters") or {}
            if isinstance(req_params, dict):
                for k, v in req_params.items():
                    if v is not None and isinstance(v, (str, int, float, bool)):
                        extra[f"requestParameters.{k}"] = str(v)[:200]
            # Include identity type
            identity_type = identity.get("type")
            if identity_type:
                extra["identityType"] = str(identity_type)

            event = NormalizedEvent(
                timestamp=ts,
                source_type="cloudtrail",
                hostname=normalize_entity(event_source),
                username=normalize_entity(username),
                source_ip=normalize_entity(source_ip),
                event_type=event_type,
                event_id=event_name,
                raw_message=raw_msg,
                flags=flags,
                extra_fields=extra,
            )
            if flags:
                event.severity_hint = "high" if "sensitive_action" in flags else "medium"
            return event
        except Exception as e:
            self._log_skip(str(rec)[:120], f"cloudtrail record error: {e}")
            return None

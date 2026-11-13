"""OCSF v1.2 Normalization Mapper for Multi-Cloud Audit Logs (AWS, Azure, GCP).

Transforms raw CloudTrail, Azure Activity, and GCP Cloud Audit records into
standardized OCSF v1.2 Cloud Activity structs.
"""

from datetime import datetime, timezone
import ipaddress
import json
from typing import Any, Dict, Optional, Tuple
import uuid

from services.mod02_asset_crawler.internal.normalizer.urn_builder import build_urn
from services.mod03_ioa_siem_engine.internal.parser.schema_validator import (
    OCSFCloudActivityEvent,
    validate_ocsf_record,
)


PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _is_ip_external(ip_str: Optional[str]) -> int:
    """Returns 1 if IP is an external public/routable address, 0 if internal/RFC1918/loopback."""
    if not ip_str or not isinstance(ip_str, str):
        return 0
    clean_ip = ip_str.strip()
    try:
        ip = ipaddress.ip_address(clean_ip)
        for net in PRIVATE_NETWORKS:
            if ip in net:
                return 0
        return 1
    except ValueError:
        return 0


class OCSFMapper:
    """Normalizes CloudTrail, Azure Activity, and GCP Audit logs to OCSF v1.2."""

    @staticmethod
    def map_event(
        raw_event: Dict[str, Any],
        tenant_id: Optional[str] = None,
        provider_hint: Optional[str] = None,
    ) -> OCSFCloudActivityEvent:
        """Auto-detects cloud provider schema and transforms into validated OCSF event."""
        tid = tenant_id or str(uuid.uuid4())

        # Auto-detect provider if not explicitly provided
        provider = provider_hint.lower() if provider_hint else OCSFMapper._detect_provider(raw_event)

        if provider == "aws":
            return OCSFMapper._map_aws_cloudtrail(raw_event, tid)
        elif provider == "azure":
            return OCSFMapper._map_azure_activity(raw_event, tid)
        elif provider == "gcp":
            return OCSFMapper._map_gcp_audit(raw_event, tid)
        else:
            # Fallback generic mapping
            return OCSFMapper._map_generic(raw_event, tid)

    @staticmethod
    def _detect_provider(raw: Dict[str, Any]) -> str:
        """Infers cloud provider from key signature."""
        if "eventSource" in raw or "userIdentity" in raw or "awsRegion" in raw:
            return "aws"
        if "operationName" in raw or "subscriptionId" in raw or "resourceId" in raw:
            return "azure"
        if "protoPayload" in raw or "insertId" in raw or ("resource" in raw and "labels" in raw.get("resource", {})):
            return "gcp"
        return "aws"

    @staticmethod
    def _map_aws_cloudtrail(raw: Dict[str, Any], tenant_id: str) -> OCSFCloudActivityEvent:
        event_time = raw.get("eventTime", datetime.now(timezone.utc).isoformat())
        account_id = raw.get("recipientAccountId") or raw.get("userIdentity", {}).get("accountId", "unknown-account")
        region = raw.get("awsRegion", "global")
        event_name = raw.get("eventName", "UnknownAWSAction")

        # Determine read_only
        raw_ro = raw.get("readOnly")
        if raw_ro is not None:
            if isinstance(raw_ro, bool):
                read_only = 1 if raw_ro else 0
            elif isinstance(raw_ro, str):
                read_only = 1 if raw_ro.lower() == "true" else 0
            else:
                read_only = 1 if bool(raw_ro) else 0
        else:
            # Actions starting with Describe, List, Get are read-only
            read_only = 1 if any(event_name.startswith(p) for p in ("Get", "List", "Describe", "Lookup", "Head")) else 0

        # Actor identity
        user_identity = raw.get("userIdentity", {})
        actor_arn = (
            user_identity.get("arn")
            or user_identity.get("principalId")
            or user_identity.get("userName")
            or f"arn:aws:iam::{account_id}:unknown"
        )

        mfa_flag = 0
        session_ctx = user_identity.get("sessionContext", {})
        mfa_val = session_ctx.get("attributes", {}).get("mfaAuthenticated")
        if mfa_val is True or str(mfa_val).lower() == "true":
            mfa_flag = 1

        src_ip = raw.get("sourceIPAddress", "0.0.0.0")
        is_external = _is_ip_external(src_ip)

        # Target resource extraction
        target_urn = OCSFMapper._extract_aws_target_urn(raw, account_id, region, event_name)

        error_code = raw.get("errorCode")
        status_code = "Failure" if error_code else "Success"

        record = {
            "tenant_id": tenant_id,
            "event_time": event_time,
            "provider": "aws",
            "account_id": str(account_id),
            "region": region,
            "event_name": event_name,
            "read_only": read_only,
            "actor_user_arn": actor_arn,
            "actor_session_mfa": mfa_flag,
            "src_ip": src_ip,
            "is_external_ip": is_external,
            "geo_country": raw.get("geoCountry", "US"),
            "target_resource_urn": target_urn,
            "status_code": status_code,
            "error_code": error_code,
            "raw_event_json": json.dumps(raw),
        }
        return validate_ocsf_record(record)

    @staticmethod
    def _extract_aws_target_urn(raw: Dict[str, Any], account_id: str, region: str, event_name: str) -> str:
        # 1. From resources list
        resources = raw.get("resources", [])
        if resources and isinstance(resources, list):
            first_res = resources[0]
            arn = first_res.get("ARN") or first_res.get("arn")
            if arn:
                # Convert ARN into standard URN
                parts = arn.split(":")
                service = parts[2] if len(parts) > 2 else "cloud"
                res_type = parts[5].split("/")[0] if len(parts) > 5 and "/" in parts[5] else "resource"
                res_id = parts[5].split("/")[-1] if len(parts) > 5 and "/" in parts[5] else (parts[5] if len(parts) > 5 else "unknown")
                return build_urn("aws", account_id, region, service, res_type, res_id)

        # 2. From requestParameters
        params = raw.get("requestParameters") or {}
        if "roleArn" in params:
            role_arn = params["roleArn"]
            return build_urn("aws", account_id, "global", "iam", "aws_iam_role", role_arn.split("/")[-1])
        if "bucketName" in params:
            return build_urn("aws", account_id, region, "s3", "aws_s3_bucket", params["bucketName"])
        if "groupId" in params:
            return build_urn("aws", account_id, region, "ec2", "aws_security_group", params["groupId"])
        if "functionName" in params:
            return build_urn("aws", account_id, region, "lambda", "aws_lambda_function", params["functionName"])
        if "instanceId" in params:
            return build_urn("aws", account_id, region, "ec2", "aws_instance", params["instanceId"])

        # Fallback default
        return build_urn("aws", account_id, region, "cloud", "aws_action", event_name.lower())

    @staticmethod
    def _map_azure_activity(raw: Dict[str, Any], tenant_id: str) -> OCSFCloudActivityEvent:
        event_time = raw.get("eventTimestamp") or raw.get("time", datetime.now(timezone.utc).isoformat())
        account_id = raw.get("subscriptionId", "unknown-subscription")
        region = raw.get("resourceLocation", raw.get("location", "global"))

        op_name = raw.get("operationName")
        if isinstance(op_name, dict):
            event_name = op_name.get("value", "UnknownAzureOperation")
        else:
            event_name = str(op_name or "UnknownAzureOperation")

        read_only = 0
        if any(w in event_name.lower() for w in ("read", "get", "list")):
            read_only = 1

        actor_arn = str(raw.get("caller") or f"/subscriptions/{account_id}/providers/Microsoft.AAD/users/unknown")
        src_ip = raw.get("callerIpAddress") or raw.get("clientIp", "0.0.0.0")
        is_external = _is_ip_external(src_ip)

        resource_id = raw.get("resourceId") or f"/subscriptions/{account_id}/resourceGroups/default/providers/microsoft.cloud/{event_name}"
        clean_res_id = resource_id.strip("/")
        parts = clean_res_id.split("/")
        service = "azure_core"
        rtype = "azure_resource"
        rid = parts[-1]
        for i, p in enumerate(parts):
            if p.lower() == "providers" and i + 1 < len(parts):
                service = parts[i + 1].split(".")[-1].lower()
                if i + 2 < len(parts):
                    rtype = parts[i + 2].lower()
                break

        target_urn = build_urn("azure", account_id, region, service, rtype, rid)

        status_raw = raw.get("status")
        status_val = status_raw.get("value", "Success") if isinstance(status_raw, dict) else str(status_raw or "Success")
        sub_status = raw.get("subStatus", {})
        error_code = sub_status.get("value") if isinstance(sub_status, dict) else (raw.get("errorCode") or None)

        record = {
            "tenant_id": tenant_id,
            "event_time": event_time,
            "provider": "azure",
            "account_id": str(account_id),
            "region": region,
            "event_name": event_name,
            "read_only": read_only,
            "actor_user_arn": actor_arn,
            "actor_session_mfa": 0,
            "src_ip": src_ip,
            "is_external_ip": is_external,
            "geo_country": raw.get("geoCountry", "US"),
            "target_resource_urn": target_urn,
            "status_code": status_val,
            "error_code": error_code,
            "raw_event_json": json.dumps(raw),
        }
        return validate_ocsf_record(record)

    @staticmethod
    def _map_gcp_audit(raw: Dict[str, Any], tenant_id: str) -> OCSFCloudActivityEvent:
        event_time = raw.get("timestamp", datetime.now(timezone.utc).isoformat())
        resource = raw.get("resource", {})
        labels = resource.get("labels", {})
        account_id = labels.get("project_id", "unknown-gcp-project")
        region = labels.get("location") or labels.get("zone", "global")

        proto = raw.get("protoPayload", {})
        event_name = proto.get("methodName", "UnknownGCPMethod")

        read_only = 0
        if any(p in event_name.lower() for p in ("get", "list")):
            read_only = 1

        auth_info = proto.get("authenticationInfo", {})
        actor_arn = auth_info.get("principalEmail") or f"projects/{account_id}/serviceAccounts/unknown"

        req_meta = proto.get("requestMetadata", {})
        src_ip = req_meta.get("callerIp", "0.0.0.0")
        is_external = _is_ip_external(src_ip)

        res_name = proto.get("resourceName") or f"projects/{account_id}/global/unknown"
        # Parse GCP resource name
        parts = res_name.strip("/").split("/")
        service = "gcp_core"
        rtype = "gcp_resource"
        rid = parts[-1]
        if "googleapis.com" in res_name:
            service = parts[0].replace(".googleapis.com", "").replace("//", "")
        if len(parts) >= 3:
            rtype = parts[-2]

        target_urn = build_urn("gcp", account_id, region, service, rtype, rid)

        status_obj = proto.get("status", {})
        error_code = None
        code = status_obj.get("code", 0)
        status_code = "Success"
        if code != 0:
            status_code = "Failure"
            error_code = status_obj.get("message") or f"ErrorCode_{code}"

        record = {
            "tenant_id": tenant_id,
            "event_time": event_time,
            "provider": "gcp",
            "account_id": str(account_id),
            "region": region,
            "event_name": event_name,
            "read_only": read_only,
            "actor_user_arn": actor_arn,
            "actor_session_mfa": 0,
            "src_ip": src_ip,
            "is_external_ip": is_external,
            "geo_country": raw.get("geoCountry", "US"),
            "target_resource_urn": target_urn,
            "status_code": status_code,
            "error_code": error_code,
            "raw_event_json": json.dumps(raw),
        }
        return validate_ocsf_record(record)

    @staticmethod
    def _map_generic(raw: Dict[str, Any], tenant_id: str) -> OCSFCloudActivityEvent:
        account_id = raw.get("account_id", "default")
        region = raw.get("region", "global")
        event_name = raw.get("event_name", "generic_event")
        actor = raw.get("actor", "system")
        src_ip = raw.get("src_ip", "0.0.0.0")
        target_urn = build_urn("aws", account_id, region, "generic", "generic_resource", "res-1")

        record = {
            "tenant_id": tenant_id,
            "event_time": datetime.now(timezone.utc).isoformat(),
            "provider": "aws",
            "account_id": str(account_id),
            "region": region,
            "event_name": event_name,
            "read_only": 0,
            "actor_user_arn": actor,
            "actor_session_mfa": 0,
            "src_ip": src_ip,
            "is_external_ip": _is_ip_external(src_ip),
            "geo_country": "US",
            "target_resource_urn": target_urn,
            "status_code": "Success",
            "error_code": None,
            "raw_event_json": json.dumps(raw),
        }
        return validate_ocsf_record(record)

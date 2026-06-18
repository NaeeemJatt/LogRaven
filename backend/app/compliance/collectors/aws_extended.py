# LogRaven — Deep AWS evidence collectors
#
# Each collector reads read-only AWS APIs and returns PII-FREE aggregates
# (counts / booleans / percentages). Every call degrades gracefully: if a
# permission is missing or a service is not enabled, the corresponding signal
# resolves to None ("unknown") rather than raising, so frameworks can still be
# graded on whatever evidence is available.
#
# These outputs feed app.compliance.signals.build_evidence_signals via the
# sanitized-evidence sections: iam_extended, cloudtrail_config, encryption,
# network, monitoring, backup.

from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timezone
from typing import Any, Callable

from botocore.exceptions import BotoCoreError, ClientError

from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_REGION = "us-east-1"
_MAX_ITEMS = 200                      # cap per paginated resource scan
_STALE_KEY_DAYS = 90
_SENSITIVE_PORTS = {22, 3389, 3306, 5432, 1433, 6379, 27017, 9200, 23, 21}
ADMIN_POLICY_ARN = "arn:aws:iam::aws:policy/AdministratorAccess"


def _region(session, region: str | None) -> str:
    return region or session.region_name or DEFAULT_REGION


def _safe(label: str, fn: Callable[[], Any], default: Any = None) -> Any:
    """Run a collector call, swallowing AWS/permission errors into a default."""
    try:
        return fn()
    except (ClientError, BotoCoreError) as exc:
        logger.info("Extended collector '%s' unavailable: %s", label, exc)
        return default
    except Exception as exc:  # noqa: BLE001 - never let evidence collection crash the audit
        logger.warning("Extended collector '%s' error: %s", label, exc)
        return default


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator * 100.0, 2)


# ── IAM (deep) ──────────────────────────────────────────────────────────────

def collect_iam_extended(session, region: str | None = None) -> dict[str, Any]:
    iam = session.client("iam", region_name=_region(session, region))
    result: dict[str, Any] = {
        "stale_access_keys": None,
        "admin_users": None,
        "access_analyzer_external_findings": None,
    }

    def _stale_keys() -> int | None:
        # Credential report may need a moment to generate.
        for _ in range(3):
            state = iam.generate_credential_report().get("State")
            if state == "COMPLETE":
                break
            time.sleep(1)
        report = iam.get_credential_report().get("Content", b"")
        text = report.decode("utf-8") if isinstance(report, bytes) else str(report)
        reader = csv.DictReader(io.StringIO(text))
        now = datetime.now(timezone.utc)
        stale = 0
        for row in reader:
            for col in ("access_key_1_last_rotated", "access_key_2_last_rotated"):
                val = row.get(col, "")
                if val and val not in ("N/A", "no_information", "not_supported"):
                    try:
                        rotated = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        if (now - rotated).days > _STALE_KEY_DAYS:
                            stale += 1
                    except ValueError:
                        continue
        return stale

    def _admins() -> int:
        resp = iam.list_entities_for_policy(PolicyArn=ADMIN_POLICY_ARN)
        return (
            len(resp.get("PolicyUsers", []))
            + len(resp.get("PolicyRoles", []))
            + len(resp.get("PolicyGroups", []))
        )

    def _analyzer_findings() -> int | None:
        aa = session.client("accessanalyzer", region_name=_region(session, region))
        analyzers = aa.list_analyzers().get("analyzers", [])
        if not analyzers:
            return None
        arn = analyzers[0]["arn"]
        findings = aa.list_findings_v2(
            analyzerArn=arn,
            filter={"status": {"eq": ["ACTIVE"]}},
            maxResults=_MAX_ITEMS,
        ).get("findings", [])
        return len(findings)

    result["stale_access_keys"] = _safe("iam_credential_report", _stale_keys)
    result["admin_users"] = _safe("iam_admin_entities", _admins)
    result["access_analyzer_external_findings"] = _safe("access_analyzer", _analyzer_findings)
    return result


# ── CloudTrail configuration ─────────────────────────────────────────────────

def collect_cloudtrail_config(session, region: str | None = None) -> dict[str, Any]:
    result = {"multi_region": None, "log_file_validation": None, "kms_encrypted": None}

    def _trails() -> dict[str, Any]:
        ct = session.client("cloudtrail", region_name=_region(session, region))
        trails = ct.describe_trails(includeShadowTrails=False).get("trailList", [])
        if not trails:
            return {"multi_region": False, "log_file_validation": False, "kms_encrypted": False}
        return {
            "multi_region": any(t.get("IsMultiRegionTrail") for t in trails),
            "log_file_validation": any(t.get("LogFileValidationEnabled") for t in trails),
            "kms_encrypted": any(bool(t.get("KmsKeyId")) for t in trails),
        }

    return _safe("cloudtrail_config", _trails, result) or result


# ── Encryption at rest ───────────────────────────────────────────────────────

def collect_encryption(session, region: str | None = None) -> dict[str, Any]:
    reg = _region(session, region)
    result: dict[str, Any] = {
        "s3_default_encryption_rate": None,
        "s3_public_access_blocked": None,
        "ebs_default_encryption": None,
        "rds_encryption_rate": None,
        "kms_key_rotation_rate": None,
    }

    def _s3_encryption() -> float | None:
        s3 = session.client("s3")
        buckets = s3.list_buckets().get("Buckets", [])[:_MAX_ITEMS]
        if not buckets:
            return None
        encrypted = 0
        for bucket in buckets:
            try:
                s3.get_bucket_encryption(Bucket=bucket["Name"])
                encrypted += 1
            except ClientError:
                continue
        return _rate(encrypted, len(buckets))

    def _s3_public_block() -> bool | None:
        sts = session.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        s3control = session.client("s3control", region_name=reg)
        cfg = s3control.get_public_access_block(AccountId=account_id).get(
            "PublicAccessBlockConfiguration", {}
        )
        return all(
            cfg.get(k, False)
            for k in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
        )

    def _ebs_default() -> bool:
        ec2 = session.client("ec2", region_name=reg)
        return bool(ec2.get_ebs_encryption_by_default().get("EbsEncryptionByDefault"))

    def _rds_encryption() -> float | None:
        rds = session.client("rds", region_name=reg)
        instances = rds.describe_db_instances().get("DBInstances", [])[:_MAX_ITEMS]
        if not instances:
            return None
        encrypted = sum(1 for db in instances if db.get("StorageEncrypted"))
        return _rate(encrypted, len(instances))

    def _kms_rotation() -> float | None:
        kms = session.client("kms", region_name=reg)
        keys = kms.list_keys().get("Keys", [])[:_MAX_ITEMS]
        if not keys:
            return None
        customer_keys = 0
        rotated = 0
        for key in keys:
            try:
                meta = kms.describe_key(KeyId=key["KeyId"]).get("KeyMetadata", {})
                if meta.get("KeyManager") != "CUSTOMER" or meta.get("KeyState") != "Enabled":
                    continue
                customer_keys += 1
                status = kms.get_key_rotation_status(KeyId=key["KeyId"])
                if status.get("KeyRotationEnabled"):
                    rotated += 1
            except ClientError:
                continue
        return _rate(rotated, customer_keys)

    result["s3_default_encryption_rate"] = _safe("s3_encryption", _s3_encryption)
    result["s3_public_access_blocked"] = _safe("s3_public_block", _s3_public_block)
    result["ebs_default_encryption"] = _safe("ebs_default_encryption", _ebs_default)
    result["rds_encryption_rate"] = _safe("rds_encryption", _rds_encryption)
    result["kms_key_rotation_rate"] = _safe("kms_rotation", _kms_rotation)
    return result


# ── Network ──────────────────────────────────────────────────────────────────

def collect_network(session, region: str | None = None) -> dict[str, Any]:
    reg = _region(session, region)
    result: dict[str, Any] = {
        "vpc_flow_logs_enabled": None,
        "open_security_groups": None,
        "default_sg_restricted": None,
    }

    def _flow_logs() -> bool:
        ec2 = session.client("ec2", region_name=reg)
        return len(ec2.describe_flow_logs().get("FlowLogs", [])) > 0

    def _security_groups() -> dict[str, Any]:
        ec2 = session.client("ec2", region_name=reg)
        groups = ec2.describe_security_groups().get("SecurityGroups", [])[:_MAX_ITEMS]
        open_count = 0
        default_restricted = True
        for sg in groups:
            for perm in sg.get("IpPermissions", []):
                public = any(r.get("CidrIp") == "0.0.0.0/0" for r in perm.get("IpRanges", []))
                if not public:
                    continue
                from_port = perm.get("FromPort")
                to_port = perm.get("ToPort")
                if from_port is None or perm.get("IpProtocol") == "-1":
                    open_count += 1
                elif any(from_port <= p <= (to_port or from_port) for p in _SENSITIVE_PORTS):
                    open_count += 1
            if sg.get("GroupName") == "default" and sg.get("IpPermissions"):
                default_restricted = False
        return {"open_security_groups": open_count, "default_sg_restricted": default_restricted}

    sg_result = _safe("security_groups", _security_groups)
    if isinstance(sg_result, dict):
        result.update(sg_result)
    result["vpc_flow_logs_enabled"] = _safe("vpc_flow_logs", _flow_logs)
    return result


# ── Monitoring & detection ───────────────────────────────────────────────────

def collect_monitoring(session, region: str | None = None) -> dict[str, Any]:
    reg = _region(session, region)
    result: dict[str, Any] = {
        "config_recorder_enabled": None,
        "securityhub_enabled": None,
        "inspector_enabled": None,
        "min_log_retention_days": None,
        "security_alarms_configured": None,
    }

    def _config() -> bool:
        cfg = session.client("config", region_name=reg)
        statuses = cfg.describe_configuration_recorder_status().get("ConfigurationRecordersStatus", [])
        return any(s.get("recording") for s in statuses)

    def _securityhub() -> bool:
        sh = session.client("securityhub", region_name=reg)
        sh.describe_hub()  # raises if not enabled
        return True

    def _inspector() -> bool:
        sts = session.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        ins = session.client("inspector2", region_name=reg)
        resp = ins.batch_get_account_status(accountIds=[account_id]).get("accounts", [])
        return any(a.get("state", {}).get("status") == "ENABLED" for a in resp)

    def _retention() -> int | None:
        logs = session.client("logs", region_name=reg)
        groups = logs.describe_log_groups(limit=50).get("logGroups", [])
        retentions = [g["retentionInDays"] for g in groups if g.get("retentionInDays")]
        return min(retentions) if retentions else None

    def _alarms() -> bool:
        cw = session.client("cloudwatch", region_name=reg)
        alarms = cw.describe_alarms(MaxRecords=20).get("MetricAlarms", [])
        return len(alarms) > 0

    result["config_recorder_enabled"] = _safe("config_recorder", _config)
    result["securityhub_enabled"] = _safe("securityhub", _securityhub, default=False)
    result["inspector_enabled"] = _safe("inspector", _inspector)
    result["min_log_retention_days"] = _safe("log_retention", _retention)
    result["security_alarms_configured"] = _safe("cloudwatch_alarms", _alarms)
    return result


# ── Resilience / backup ──────────────────────────────────────────────────────

def collect_backup(session, region: str | None = None) -> dict[str, Any]:
    reg = _region(session, region)
    result: dict[str, Any] = {"backup_configured": None, "rds_backups_enabled": None}

    def _backup_plans() -> bool:
        backup = session.client("backup", region_name=reg)
        return len(backup.list_backup_plans().get("BackupPlansList", [])) > 0

    def _rds_backups() -> bool | None:
        rds = session.client("rds", region_name=reg)
        instances = rds.describe_db_instances().get("DBInstances", [])[:_MAX_ITEMS]
        if not instances:
            return None
        return all(db.get("BackupRetentionPeriod", 0) > 0 for db in instances)

    result["backup_configured"] = _safe("backup_plans", _backup_plans)
    result["rds_backups_enabled"] = _safe("rds_backups", _rds_backups)
    return result


# ── Orchestration ─────────────────────────────────────────────────────────────

def collect_extended_evidence(session, region: str | None = None) -> dict[str, Any]:
    """
    Run all deep collectors. Returns sanitized (PII-free) sections keyed to match
    app.compliance.signals.build_evidence_signals. Individual sections degrade to
    'unknown' values on missing permissions without failing the audit.
    """
    logger.info("Collecting extended AWS evidence (deep collectors)...")
    evidence = {
        "iam_extended": collect_iam_extended(session, region),
        "cloudtrail_config": collect_cloudtrail_config(session, region),
        "encryption": collect_encryption(session, region),
        "network": collect_network(session, region),
        "monitoring": collect_monitoring(session, region),
        "backup": collect_backup(session, region),
    }
    logger.info("Extended evidence collection complete")
    return evidence

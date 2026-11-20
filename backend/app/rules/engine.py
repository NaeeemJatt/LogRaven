# LogRaven — Rule Engine
#
# PURPOSE:
#   Deterministic detection rules applied to normalized events before AI analysis.
#   Rule engine runs FIRST. AI writes narrative, not detections.
#
# RULES:
#   Rule 1 — Brute force (high):    5+ auth_failure from same IP in 60s window
#   Rule 2 — Brute force (critical): >20 auth_failure from same IP (high volume)
#   Rule 3 — Lateral movement:       events already flagged by parsers are re-checked
#   Rule 4 — Deduplication:          3+ identical raw_message[:100] within 5s window

from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from app.rules.evaluator import RuleMatch, evaluate_rule, extract_path
from app.rules.loader import RuleLoader, get_default_rule_loader
from app.rules.schema import (
    DeterministicRuleSpec,
    RuleDefinition,
    SimpleCondition,
    SimpleMatch,
    ThresholdMatch,
)
from app.utils.logger import get_logger

logger = get_logger("lograven.rules.engine")


_BRUTE_FORCE_HIGH_RULE = RuleDefinition(
    id="lr-builtin-core-brute-force-high",
    title="Authentication Brute Force",
    severity="high",
    mitre_technique_id="T1110",
    mitre_tactic="credential-access",
    flag="brute_force_candidate",
    description="Five or more authentication failures from one source IP occurred within 60 seconds.",
    match=ThresholdMatch(
        type="threshold",
        event_type="auth_failure",
        group_by="source_ip",
        count=5,
        window_seconds=60,
    ),
)
_BRUTE_FORCE_CRITICAL_RULE = RuleDefinition(
    id="lr-builtin-core-brute-force-critical",
    title="High-Volume Authentication Brute Force",
    severity="critical",
    mitre_technique_id="T1110",
    mitre_tactic="credential-access",
    flag="brute_force_candidate",
    description="More than 20 authentication failures originated from one source IP.",
    match=ThresholdMatch(
        type="threshold",
        event_type="auth_failure",
        group_by="source_ip",
        count=21,
        window_seconds=2_147_483_647,
    ),
)
_LATERAL_MOVEMENT_RULE = RuleDefinition(
    id="lr-builtin-core-lateral-movement",
    title="Lateral Movement Candidate",
    severity="high",
    mitre_technique_id="T1021",
    mitre_tactic="lateral-movement",
    flag="lateral_movement_candidate",
    description="Authentication activity indicates possible movement between systems.",
    match=SimpleMatch(
        type="simple",
        conditions=[
            SimpleCondition(
                field="flags",
                op="contains",
                value="lateral_movement_candidate",
            )
        ],
    ),
)
_SENSITIVE_ACTION_RULE = RuleDefinition(
    id="lr-builtin-core-sensitive-action",
    title="Sensitive Cloud Action",
    severity="high",
    flag="sensitive_action",
    description="A security-sensitive cloud control-plane action was observed.",
    match=SimpleMatch(
        type="simple",
        conditions=[
            SimpleCondition(
                field="flags",
                op="contains",
                value="sensitive_action",
            )
        ],
    ),
)


def _run_builtin_rules_with_matches(events: list) -> tuple[list, list[RuleMatch]]:
    """
    Apply deterministic detection rules to normalized events.
    Returns the same list with severity_hint and flags updated.
    No AI. Pure Python logic only.
    """
    from collections import defaultdict

    if not events:
        return events, []

    # Rule 1 — Critical brute force
    # IP with 5+ auth_failure events within any 60-second window
    ip_failures = defaultdict(list)
    for event in events:
        if event.event_type == "auth_failure" and event.source_ip:
            ip_failures[event.source_ip].append(event.timestamp)

    brute_force_ips = set()
    for ip, timestamps in ip_failures.items():
        sorted_ts = sorted([t for t in timestamps if t is not None])
        for i in range(len(sorted_ts)):
            window = [
                t for t in sorted_ts[i:]
                if (t - sorted_ts[i]).total_seconds() <= 60
            ]
            if len(window) >= 5:
                brute_force_ips.add(ip)
                break

    # Rule 2 — Critical brute force with >20 failures
    high_volume_ips = {
        ip for ip, ts in ip_failures.items() if len(ts) > 20
    }
    high_only_ips = brute_force_ips - high_volume_ips

    # Rule 3 — Lateral movement
    # Events with lateral_movement_candidate flag already set by parsers

    # Rule 4 — Deduplication within 5-second windows
    # Group events by raw_message, mark duplicates
    message_groups = defaultdict(list)
    for event in events:
        key = event.raw_message[:100] if event.raw_message else ""
        message_groups[key].append(event)

    for key, group in message_groups.items():
        if len(group) < 3:
            continue
        sorted_group = sorted(
            [e for e in group if e.timestamp is not None],
            key=lambda e: e.timestamp
        )
        for i in range(len(sorted_group)):
            window = [
                e for e in sorted_group[i:]
                if (e.timestamp - sorted_group[i].timestamp).total_seconds() <= 5
            ]
            if len(window) >= 3:
                # Keep first, mark rest as deduplicated
                for e in window[1:]:
                    if "deduplicated" not in e.flags:
                        e.flags.append("deduplicated")
                    e.severity_hint = "deduplicated"

    # Apply severity hints based on rules
    for event in events:
        if event.source_ip in high_volume_ips:
            event.severity_hint = "critical"
            if "brute_force_candidate" not in event.flags:
                event.flags.append("brute_force_candidate")
        elif event.source_ip in brute_force_ips:
            if event.severity_hint not in ("critical", "high"):
                event.severity_hint = "high"
            if "brute_force_candidate" not in event.flags:
                event.flags.append("brute_force_candidate")
        elif "lateral_movement_candidate" in event.flags:
            if event.severity_hint not in ("critical",):
                event.severity_hint = "high"
        elif "sensitive_action" in event.flags:
            if event.severity_hint not in ("critical", "high"):
                event.severity_hint = "high"

    high_events = [
        event
        for event in events
        if event.event_type == "auth_failure"
        and event.source_ip in high_only_ips
    ]
    critical_events = [
        event
        for event in events
        if event.event_type == "auth_failure"
        and event.source_ip in high_volume_ips
    ]
    lateral_events = [
        event
        for event in events
        if "lateral_movement_candidate" in event.flags
    ]
    sensitive_events = [
        event
        for event in events
        if "sensitive_action" in event.flags
    ]

    matches: list[RuleMatch] = []
    for rule, matched_events in (
        (_BRUTE_FORCE_HIGH_RULE, high_events),
        (_BRUTE_FORCE_CRITICAL_RULE, critical_events),
        (_LATERAL_MOVEMENT_RULE, lateral_events),
        (_SENSITIVE_ACTION_RULE, sensitive_events),
    ):
        if matched_events:
            matches.append(RuleMatch(rule=rule, events=matched_events))
    return events, matches


def _run_builtin_rules(events: list) -> list:
    """Compatibility entry point returning only built-in event mutations."""
    return _run_builtin_rules_with_matches(events)[0]


def run_rules_with_matches(events: list) -> tuple[list, list]:
    """Apply built-in and YAML rules, returning all explicit rule matches."""
    events, matches = _run_builtin_rules_with_matches(events)
    try:
        from app.rules.loader import get_rules
        from app.rules.evaluator import run_yaml_rules_with_matches

        yaml_rules = get_rules()
        if yaml_rules:
            events, yaml_matches = run_yaml_rules_with_matches(events, yaml_rules)
            matches.extend(yaml_matches)
    except Exception as exc:
        # Rule engine failure must never block the pipeline
        from app.utils.logger import get_logger

        get_logger("lograven.rules").error("YAML rule evaluation failed: %s", exc, exc_info=True)
    return events, matches


def run_rules(events: list) -> list:
    """
    Compatibility entry point: apply deterministic rules and return events.
    """
    return run_rules_with_matches(events)[0]


def rule_matches_to_findings(matches: list, event_source_files: dict[int, str]) -> list[dict]:
    """Convert explicit rule matches into report-ready deterministic findings."""
    findings: list[dict] = []
    for match in matches:
        timestamps = sorted(event.timestamp for event in match.events if event.timestamp is not None)
        first_seen = timestamps[0].isoformat() if timestamps else None
        last_seen = timestamps[-1].isoformat() if timestamps else None
        source_files = sorted({
            event_source_files[id(event)]
            for event in match.events
            if id(event) in event_source_files
        })
        evidence = f"Matched {len(match.events)} events"
        if first_seen and last_seen:
            evidence += f" from {first_seen} to {last_seen}"
        evidence += "."
        description = match.rule.description.strip()
        if description:
            description = f"{description}\n\n{evidence}"
        else:
            description = evidence

        findings.append({
            "severity": match.rule.severity,
            "title": match.rule.title,
            "description": description,
            "mitre_technique_id": match.rule.mitre_technique_id,
            "mitre_technique_name": None,
            "mitre_tactic": match.rule.mitre_tactic,
            "iocs": [],
            "remediation": None,
            "finding_type": "single",
            "confidence": 1.0,
            "source_files": source_files,
            "match_count": len(match.events),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "rule_id": match.rule.id,
        })
    return findings


# ── Tri-Path Real-Time AWS Log Stream & Mutating Drift Engine ─────────────────

class RuleEngine:
    """
    Real-Time AWS CloudTrail & Mutating Drift Engine (FR-DET-05).
    Handles 3 evaluation paths simultaneously on every AWS CloudTrail event:
    1. Sliding-window log correlation rules.
    2. Direct Qualys runtime log controls (CID 18, CID 27–40).
    3. Instant configuration-drift extraction from mutating requestParameters.
    """

    def __init__(self, loader: Optional[RuleLoader] = None):
        self.loader = loader if loader is not None else get_default_rule_loader()
        self.windows: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

    def process_cloudtrail_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes a single AWS CloudTrail event across all 3 detection & drift paths.
        Returns a list of structured alert findings.
        """
        alerts: List[Dict[str, Any]] = []
        now = time.time()
        evt_name = event.get("eventName", "")
        req_params = event.get("requestParameters") or {}
        actor_arn = extract_path(event, "$.userIdentity.arn") or extract_path(event, "$.userIdentity.principalId")
        src_ip = event.get("sourceIPAddress")

        # ── Path A & B: Sliding-window log correlation & Qualys runtime controls ───
        for rule in self.loader.get_log_rules("AWS"):
            if evaluate_rule(event, rule):
                group_key = (
                    "|".join(str(extract_path(event, g) or "") for g in rule.group_by_fields)
                    if rule.group_by_fields
                    else "global"
                )
                w_key = (rule.rule_id, group_key)

                if rule.window_seconds > 0 and rule.threshold_count > 1:
                    q = self.windows[w_key]
                    q.append(now)
                    while q and q[0] < now - rule.window_seconds:
                        q.popleft()
                    if len(q) < rule.threshold_count:
                        continue

                alerts.append({
                    "rule_id": rule.rule_id,
                    "cid": rule.cid,
                    "title": rule.title,
                    "criticality": rule.criticality,
                    "service": rule.service,
                    "event_name": evt_name,
                    "actor_arn": actor_arn,
                    "src_ip": src_ip,
                    "detection_mode": "REALTIME_CLOUDTRAIL_LOG",
                    "timestamp": event.get("eventTime"),
                })

        # ── Path C: Mutating Drift Extraction from requestParameters ──────────────

        # 1. IAM Mutating Actions: PutRolePolicy, CreatePolicy, PutUserPolicy, PutGroupPolicy
        if evt_name in ("PutRolePolicy", "CreatePolicy", "PutUserPolicy", "PutGroupPolicy") and "policyDocument" in req_params:
            synthetic_iam = {"PolicyDocuments": [req_params["policyDocument"]]}
            for rule in self.loader.get_rules_for_service("AWS", "IAM", "aws_config_state"):
                if evaluate_rule(synthetic_iam, rule):
                    alerts.append({
                        "rule_id": rule.rule_id,
                        "cid": rule.cid,
                        "title": rule.title,
                        "criticality": rule.criticality,
                        "service": "IAM",
                        "event_name": evt_name,
                        "actor_arn": actor_arn,
                        "src_ip": src_ip,
                        "detection_mode": "CLOUDTRAIL_INLINE_DRIFT",
                        "drift_details": {
                            "action": evt_name,
                            "policy_document": req_params["policyDocument"],
                        },
                        "timestamp": event.get("eventTime"),
                    })

        # 2. VPC Security Group Mutating Actions: AuthorizeSecurityGroupIngress
        elif evt_name == "AuthorizeSecurityGroupIngress" and "ipPermissions" in req_params:
            ip_perms_raw = req_params["ipPermissions"]
            items = ip_perms_raw.get("items", ip_perms_raw) if isinstance(ip_perms_raw, dict) else ip_perms_raw

            synthetic_sg = {
                "IpPermissions": [
                    {
                        "FromPort": i.get("fromPort") or i.get("FromPort"),
                        "ToPort": i.get("toPort") or i.get("ToPort"),
                        "IpProtocol": i.get("ipProtocol") or i.get("IpProtocol"),
                        "IpRanges": [
                            {"CidrIp": r.get("cidrIp") or r.get("CidrIp")}
                            for r in (i.get("ipRanges", {}).get("items", []) if isinstance(i.get("ipRanges"), dict) else i.get("IpRanges", []))
                        ],
                        "Ipv6Ranges": [
                            {"CidrIpv6": r.get("cidrIpv6") or r.get("CidrIpv6")}
                            for r in (i.get("ipv6Ranges", {}).get("items", []) if isinstance(i.get("ipv6Ranges"), dict) else i.get("Ipv6Ranges", []))
                        ],
                    }
                    for i in (items if isinstance(items, list) else [])
                ]
            }

            for rule in self.loader.get_rules_for_service("AWS", "VPC", "aws_config_state"):
                if evaluate_rule(synthetic_sg, rule):
                    alerts.append({
                        "rule_id": rule.rule_id,
                        "cid": rule.cid,
                        "title": rule.title,
                        "criticality": rule.criticality,
                        "service": "VPC",
                        "event_name": evt_name,
                        "actor_arn": actor_arn,
                        "src_ip": src_ip,
                        "detection_mode": "CLOUDTRAIL_INLINE_DRIFT",
                        "drift_details": {
                            "action": evt_name,
                            "ip_permissions": synthetic_sg["IpPermissions"],
                        },
                        "timestamp": event.get("eventTime"),
                    })

        # 3. S3 Bucket Mutating Actions: PutBucketAcl, PutBucketPolicy
        elif evt_name in ("PutBucketAcl", "PutBucketPolicy"):
            is_public_drift = False
            if "accessControlPolicy" in req_params:
                acp_val = req_params["accessControlPolicy"]
                acp_str = json.dumps(acp_val) if isinstance(acp_val, (dict, list)) else str(acp_val)
                if "AllUsers" in acp_str or "AuthenticatedUsers" in acp_str:
                    is_public_drift = True

            if "policy" in req_params:
                pol_val = req_params["policy"]
                pol_str = json.dumps(pol_val) if isinstance(pol_val, (dict, list)) else str(pol_val)
                if '"*"' in pol_str and "Principal" in pol_str:
                    is_public_drift = True

            if is_public_drift:
                synthetic_s3 = {"PubliclyAccessible": True}
                for rule in self.loader.get_rules_for_service("AWS", "S3", "aws_config_state"):
                    if evaluate_rule(synthetic_s3, rule):
                        alerts.append({
                            "rule_id": rule.rule_id,
                            "cid": rule.cid,
                            "title": rule.title,
                            "criticality": rule.criticality,
                            "service": "S3",
                            "event_name": evt_name,
                            "actor_arn": actor_arn,
                            "src_ip": src_ip,
                            "detection_mode": "CLOUDTRAIL_INLINE_DRIFT",
                            "drift_details": {
                                "action": evt_name,
                                "public_exposure": True,
                            },
                            "timestamp": event.get("eventTime"),
                        })

        return alerts

    def process_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes a stream or batch of CloudTrail events and returns all aggregated alerts."""
        aggregated: List[Dict[str, Any]] = []
        for evt in events:
            aggregated.extend(self.process_cloudtrail_event(evt))
        return aggregated


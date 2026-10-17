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

from app.rules.evaluator import RuleMatch
from app.rules.schema import (
    RuleDefinition,
    SimpleCondition,
    SimpleMatch,
    ThresholdMatch,
)


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

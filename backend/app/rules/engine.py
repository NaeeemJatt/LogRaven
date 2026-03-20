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


def run_rules(events: list) -> list:
    """
    Apply deterministic detection rules to normalized events.
    Returns the same list with severity_hint and flags updated.
    No AI. Pure Python logic only.
    """
    from collections import defaultdict

    if not events:
        return events

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

    # ── YAML rule evaluation ─────────────────────────────────────────────────
    # Runs after hardcoded rules so YAML rules can build on top of parser flags.
    try:
        from app.rules.loader import get_rules
        from app.rules.evaluator import run_yaml_rules
        yaml_rules = get_rules()
        if yaml_rules:
            events = run_yaml_rules(events, yaml_rules)
    except Exception as exc:
        # Rule engine failure must never block the pipeline
        from app.utils.logger import get_logger
        get_logger("lograven.rules").error("YAML rule evaluation failed: %s", exc, exc_info=True)

    return events

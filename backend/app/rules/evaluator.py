# LogRaven — Rule Evaluator
# Applies loaded RuleDefinition objects to NormalizedEvent lists.
# Simple rules: per-event O(events × rules_per_log_type).
# Threshold rules: sliding-window aggregate O(events) per rule.

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime

from app.rules.schema import RuleDefinition, SimpleCondition, SimpleMatch, ThresholdMatch
from app.utils.logger import get_logger

logger = get_logger("lograven.rules")

_SEVERITY_RANK: dict[str, int] = {
    "critical": 5, "high": 4, "medium": 3,
    "low": 2, "informational": 1, "deduplicated": 0,
}


def _upgrade_severity(event, new_severity: str) -> None:
    """Only raise severity, never lower it."""
    if _SEVERITY_RANK.get(new_severity, 0) > _SEVERITY_RANK.get(event.severity_hint, 0):
        event.severity_hint = new_severity


def _get_field(event, field_name: str) -> str | None:
    """
    Resolve a field name against a NormalizedEvent.
    Prefix 'extra.' reads from event.extra_fields dict.
    """
    if field_name.startswith("extra."):
        key = field_name[6:]
        val = event.extra_fields.get(key)
        return str(val) if val is not None else None

    _ATTR_MAP = {
        "event_id":       event.event_id,
        "event_type":     event.event_type,
        "source_type":    event.source_type,
        "hostname":       event.hostname,
        "username":       event.username,
        "source_ip":      event.source_ip,
        "destination_ip": event.destination_ip,
        "raw_message":    event.raw_message,
        "severity_hint":  event.severity_hint,
    }
    val = _ATTR_MAP.get(field_name)
    return str(val) if val is not None else None


def _check_condition(event, cond: SimpleCondition) -> bool:
    """Return True if the condition matches the event."""
    val = _get_field(event, cond.field)
    op  = cond.op

    if op == "exists":
        result = val is not None and val != ""
    elif op == "not_exists":
        result = val is None or val == ""
    elif val is None:
        result = False
    else:
        vl = val.lower()
        cv = (cond.value or "").lower()
        vlist = [v.lower() for v in (cond.values or [])]

        if op == "eq":
            result = vl == cv
        elif op == "neq":
            result = vl != cv
        elif op == "contains":
            result = cv in vl
        elif op == "contains_any":
            result = any(v in vl for v in vlist)
        elif op == "contains_all":
            result = all(v in vl for v in vlist)
        elif op == "startswith":
            result = vl.startswith(cv)
        elif op == "endswith":
            result = vl.endswith(cv)
        elif op == "re":
            try:
                result = bool(re.search(cond.value or "", val, re.IGNORECASE))
            except re.error:
                result = False
        elif op == "in":
            result = vl in vlist
        else:
            logger.debug("Unknown operator: %s", op)
            result = False

    return (not result) if cond.negate else result


def _evaluate_simple(event, rule: RuleDefinition) -> bool:
    """Return True if this event matches the simple rule."""
    match = rule.match
    if not isinstance(match, SimpleMatch):
        return False
    if match.log_type and event.source_type != match.log_type:
        return False

    results = [_check_condition(event, c) for c in match.conditions]
    return any(results) if match.condition_logic == "or" else all(results)


def _evaluate_threshold(events: list, rule: RuleDefinition) -> None:
    """Flag events that participate in a threshold breach."""
    match = rule.match
    if not isinstance(match, ThresholdMatch):
        return

    # Filter events this rule applies to
    filtered = [
        e for e in events
        if (not match.log_type  or e.source_type == match.log_type)
        and (not match.event_type or e.event_type == match.event_type)
    ]
    if not filtered:
        return

    # Group by field
    groups: dict[str, list] = defaultdict(list)
    for ev in filtered:
        key = _get_field(ev, match.group_by)
        if key:
            groups[key].append(ev)

    # Sliding window per group
    for group_events in groups.values():
        with_ts = sorted(
            [e for e in group_events if e.timestamp is not None],
            key=lambda e: e.timestamp,
        )
        triggered = False
        for i in range(len(with_ts)):
            t0 = with_ts[i].timestamp
            window = [
                e for e in with_ts[i:]
                if (e.timestamp - t0).total_seconds() <= match.window_seconds
            ]
            if len(window) >= match.count:
                triggered = True
                break

        if triggered:
            for ev in group_events:
                if rule.flag and rule.flag not in ev.flags:
                    ev.flags.append(rule.flag)
                _upgrade_severity(ev, rule.severity)


def run_yaml_rules(events: list, rules: list[RuleDefinition]) -> list:
    """
    Apply all YAML rules to the event list, modifying events in-place.

    Returns the same events list (mutations applied).
    Logs matched rule count at INFO level.
    """
    if not events or not rules:
        return events

    # Pre-group simple rules by log_type for fast per-event lookup
    rules_by_log_type: dict[str, list[RuleDefinition]] = defaultdict(list)
    rules_any_log_type: list[RuleDefinition]            = []
    threshold_rules:    list[RuleDefinition]            = []

    for rule in rules:
        if isinstance(rule.match, SimpleMatch):
            if rule.match.log_type:
                rules_by_log_type[rule.match.log_type].append(rule)
            else:
                rules_any_log_type.append(rule)
        elif isinstance(rule.match, ThresholdMatch):
            threshold_rules.append(rule)

    matched_ids: set[str] = set()

    # ── Simple rules — per event ──────────────────────────────────────────────
    for event in events:
        relevant = rules_by_log_type.get(event.source_type, []) + rules_any_log_type
        for rule in relevant:
            if _evaluate_simple(event, rule):
                if rule.flag and rule.flag not in event.flags:
                    event.flags.append(rule.flag)
                _upgrade_severity(event, rule.severity)
                matched_ids.add(rule.id)

    # ── Threshold rules — aggregate ───────────────────────────────────────────
    for rule in threshold_rules:
        before = (
            sum(1 for e in events if rule.flag in e.flags)
            if rule.flag else 0
        )
        _evaluate_threshold(events, rule)
        after = (
            sum(1 for e in events if rule.flag in e.flags)
            if rule.flag else 0
        )
        if after > before:
            matched_ids.add(rule.id)

    logger.info("  yaml   : %d unique rules fired across %d events", len(matched_ids), len(events))
    return events

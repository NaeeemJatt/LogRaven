# LogRaven — Rule Evaluator
# Applies loaded RuleDefinition objects to NormalizedEvent lists.
#
# Performance design:
#   Simple rules are indexed by (log_type, event_id) at the start of each
#   run_yaml_rules call.  For a Windows event with EventID 4625, only the
#   rules that explicitly target EventID 4625 (plus any "catch-all" rules
#   without an event_id condition) are evaluated — typically 5–20 rules
#   instead of the full 1 800+ rule corpus.  This gives a ~100× speedup over
#   the naïve O(events × rules_per_log_type) loop.
#
#   Regex patterns are pre-compiled at rule-load time via SimpleCondition.
#   model_post_init, so there is no per-event regex compilation overhead.

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.rules.schema import RuleDefinition, SimpleCondition, SimpleMatch, ThresholdMatch
from app.utils.logger import get_logger

logger = get_logger("lograven.rules")

_SEVERITY_RANK: dict[str, int] = {
    "critical": 5, "high": 4, "medium": 3,
    "low": 2, "informational": 1, "deduplicated": 0,
}

# ── Field extraction ──────────────────────────────────────────────────────────

_DIRECT_FIELDS = frozenset({
    "event_id", "event_type", "source_type", "hostname",
    "username", "source_ip", "destination_ip", "raw_message", "severity_hint",
})


def _upgrade_severity(event, new_severity: str) -> None:
    """Only raise severity, never lower it."""
    if _SEVERITY_RANK.get(new_severity, 0) > _SEVERITY_RANK.get(event.severity_hint, 0):
        event.severity_hint = new_severity


def _get_field(event, field_name: str) -> str | None:
    if field_name.startswith("extra."):
        val = event.extra_fields.get(field_name[6:])
        return str(val) if val is not None else None
    val = getattr(event, field_name, None)
    return str(val) if val is not None else None


# ── Condition evaluation ──────────────────────────────────────────────────────

def _check_condition(event, cond: SimpleCondition) -> bool:
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

        if op == "eq":
            result = vl == cv
        elif op == "neq":
            result = vl != cv
        elif op == "contains":
            result = cv in vl
        elif op == "contains_any":
            result = any(v.lower() in vl for v in (cond.values or []))
        elif op == "contains_all":
            result = all(v.lower() in vl for v in (cond.values or []))
        elif op == "startswith":
            result = vl.startswith(cv)
        elif op == "endswith":
            result = vl.endswith(cv)
        elif op == "re":
            pattern = cond._compiled_re
            result = bool(pattern.search(val)) if pattern else False
        elif op == "in":
            result = vl in [v.lower() for v in (cond.values or [])]
        else:
            logger.debug("Unknown operator: %s", op)
            result = False

    return (not result) if cond.negate else result


def _evaluate_simple(event, rule: RuleDefinition) -> bool:
    match = rule.match
    if not isinstance(match, SimpleMatch):
        return False
    # log_type already filtered by the index — skip re-check for speed
    results = [_check_condition(event, c) for c in match.conditions]
    return any(results) if match.condition_logic == "or" else all(results)


# ── Threshold evaluation ──────────────────────────────────────────────────────

def _evaluate_threshold(events: list, rule: RuleDefinition) -> None:
    match = rule.match
    if not isinstance(match, ThresholdMatch):
        return

    filtered = [
        e for e in events
        if (not match.log_type  or e.source_type == match.log_type)
        and (not match.event_type or e.event_type == match.event_type)
    ]
    if not filtered:
        return

    groups: dict[str, list] = defaultdict(list)
    for ev in filtered:
        key = _get_field(ev, match.group_by)
        if key:
            groups[key].append(ev)

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


# ── Index builder ─────────────────────────────────────────────────────────────

def _extract_event_id_value(rule: RuleDefinition) -> str | None:
    """
    Return the literal EventID value if this rule has exactly one eq condition
    on the 'event_id' field (and it is not negated).  Otherwise return None.
    """
    match = rule.match
    if not isinstance(match, SimpleMatch):
        return None
    for cond in match.conditions:
        if (
            cond.field == "event_id"
            and cond.op == "eq"
            and not cond.negate
            and cond.value
        ):
            return cond.value.lower()
    return None


def _build_index(rules: list[RuleDefinition]):
    """
    Build a 2-level lookup:
        log_type_index[log_type][event_id]  → list of rules
        log_type_index[log_type]["_any"]    → rules without a specific event_id
        rules_any_log_type                  → rules with no log_type at all
        threshold_rules                     → ThresholdMatch rules
    """
    # log_type → event_id → [rules]
    log_type_index: dict[str, dict[str, list]] = {}
    rules_any_log_type: list[RuleDefinition] = []
    threshold_rules:    list[RuleDefinition] = []

    for rule in rules:
        if isinstance(rule.match, ThresholdMatch):
            threshold_rules.append(rule)
            continue

        if not isinstance(rule.match, SimpleMatch):
            continue

        lt = rule.match.log_type
        if not lt:
            rules_any_log_type.append(rule)
            continue

        if lt not in log_type_index:
            log_type_index[lt] = defaultdict(list)

        eid = _extract_event_id_value(rule)
        bucket = eid if eid else "_any"
        log_type_index[lt][bucket].append(rule)

    return log_type_index, rules_any_log_type, threshold_rules


# ── Public entry point ────────────────────────────────────────────────────────

def run_yaml_rules(events: list, rules: list[RuleDefinition]) -> list:
    """
    Apply all YAML rules to the event list, modifying events in-place.
    Returns the same events list (mutations applied).
    """
    if not events or not rules:
        return events

    log_type_index, rules_any_log_type, threshold_rules = _build_index(rules)

    matched_ids: set[str] = set()

    # ── Simple rules — per event, indexed lookup ──────────────────────────────
    for event in events:
        lt  = event.source_type
        eid = (str(event.event_id).lower()) if event.event_id is not None else ""

        lt_bucket = log_type_index.get(lt)
        if lt_bucket:
            # rules specific to this EventID + catch-all rules for this log_type
            relevant = lt_bucket.get(eid, []) + lt_bucket.get("_any", [])
        else:
            relevant = []

        relevant = relevant + rules_any_log_type

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

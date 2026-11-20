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

import ipaddress
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from app.rules.schema import (
    ConditionRule,
    DeterministicRuleSpec,
    OperatorType,
    RuleDefinition,
    SimpleCondition,
    SimpleMatch,
    ThresholdMatch,
)
from app.utils.logger import get_logger

logger = get_logger("lograven.rules")


@dataclass(frozen=True)
class RuleMatch:
    rule: RuleDefinition
    events: list


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

def _evaluate_threshold(events: list, rule: RuleDefinition) -> list:
    match = rule.match
    if not isinstance(match, ThresholdMatch):
        return []

    filtered = [
        e for e in events
        if (not match.log_type  or e.source_type == match.log_type)
        and (not match.event_type or e.event_type == match.event_type)
    ]
    if not filtered:
        return []

    groups: dict[str, list] = defaultdict(list)
    for ev in filtered:
        key = _get_field(ev, match.group_by)
        if key:
            groups[key].append(ev)

    matched_events: list = []
    for group_events in groups.values():
        with_ts = sorted(
            [e for e in group_events if e.timestamp is not None],
            key=lambda e: e.timestamp,
        )
        triggered_event_ids: set[int] = set()
        for i in range(len(with_ts)):
            t0 = with_ts[i].timestamp
            window = [
                e for e in with_ts[i:]
                if (e.timestamp - t0).total_seconds() <= match.window_seconds
            ]
            if len(window) >= match.count:
                triggered_event_ids.update(id(event) for event in window)

        if triggered_event_ids:
            triggered_events = [
                event for event in group_events
                if id(event) in triggered_event_ids
            ]
            matched_events.extend(triggered_events)
            for ev in triggered_events:
                if rule.flag and rule.flag not in ev.flags:
                    ev.flags.append(rule.flag)
                _upgrade_severity(ev, rule.severity)
    return matched_events


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

def run_yaml_rules_with_matches(
    events: list,
    rules: list[RuleDefinition],
) -> tuple[list, list[RuleMatch]]:
    """
    Apply all YAML rules to the event list, modifying events in-place.
    Return the same event list plus one aggregate match per fired rule.
    """
    if not events or not rules:
        return events, []

    log_type_index, rules_any_log_type, threshold_rules = _build_index(rules)
    matched_events: dict[str, list] = defaultdict(list)

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
                matched_events[rule.id].append(event)

    # ── Threshold rules — aggregate ───────────────────────────────────────────
    for rule in threshold_rules:
        matched_events[rule.id].extend(_evaluate_threshold(events, rule))

    matches: list[RuleMatch] = []
    emitted_ids: set[str] = set()
    for rule in rules:
        rule_events = matched_events.get(rule.id, [])
        if rule_events and rule.id not in emitted_ids:
            matches.append(RuleMatch(rule=rule, events=rule_events))
            emitted_ids.add(rule.id)

    logger.info("  yaml   : %d unique rules fired across %d events", len(matches), len(events))
    return events, matches


def run_yaml_rules(events: list, rules: list[RuleDefinition]) -> list:
    """Compatibility entry point returning only the mutated events."""
    return run_yaml_rules_with_matches(events, rules)[0]


# ── Deterministic (100% Non-AI) Condition & AST Evaluator ─────────────────────

def extract_path(data: Dict[str, Any], path: str) -> Any:
    """
    Extracts a nested value or list of values from data using dot-notation.
    Supports root '$', dot notation ('$.a.b'), and wildcard arrays ('$.items.*').
    """
    if path == "$" or not path:
        return data
    parts = path.lstrip("$.").split(".")

    def _walk(curr: Any, idx: int) -> Any:
        if idx == len(parts):
            return curr
        key = parts[idx]

        if key == "*":
            if isinstance(curr, list):
                out = []
                for item in curr:
                    res = _walk(item, idx + 1)
                    if isinstance(res, list):
                        out.extend(res)
                    elif res is not None:
                        out.append(res)
                return out
            elif isinstance(curr, dict):
                out = []
                for item in curr.values():
                    res = _walk(item, idx + 1)
                    if isinstance(res, list):
                        out.extend(res)
                    elif res is not None:
                        out.append(res)
                return out
            return None

        if isinstance(curr, dict):
            val = curr.get(key)
            if val is None:
                # Common AWS resource plural/singular fallbacks
                if key == "PolicyDocuments":
                    val = curr.get("PolicyDocument") or curr.get("Policies")
                    if isinstance(val, dict):
                        val = [val]
                elif key == "PolicyDocument":
                    val = curr.get("PolicyDocuments")
            return _walk(val, idx + 1)

        return None

    return _walk(data, 0)


def check_iam_ast_wildcard(policy_doc: Any, check_mode: str = "service_or_full_wildcard") -> bool:
    """
    Inspects IAM policy document AST for wildcard administrative privileges.
    Returns True if an Allow statement includes wildcard Action and Resource.
    """
    if isinstance(policy_doc, str):
        try:
            policy_doc = json.loads(unquote(policy_doc))
        except Exception:
            try:
                policy_doc = json.loads(policy_doc)
            except Exception:
                return False

    if not isinstance(policy_doc, dict):
        return False

    stmts = policy_doc.get("Statement", [])
    if isinstance(stmts, dict):
        stmts = [stmts]
    elif not isinstance(stmts, list):
        return False

    for st in stmts:
        if not isinstance(st, dict) or st.get("Effect") != "Allow":
            continue

        actions = st.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        elif not isinstance(actions, list):
            actions = []

        resources = st.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]
        elif not isinstance(resources, list):
            resources = []

        has_wild_res = any(r == "*" or (isinstance(r, str) and r.endswith(":*")) for r in resources)

        if check_mode == "full_admin":
            if "*" in actions and "*" in resources:
                return True
        else:
            if has_wild_res and any(a == "*" or (isinstance(a, str) and a.endswith(":*")) for a in actions):
                return True

    return False


def check_cidr_open_world(permissions: Any, target_port: Optional[int] = None) -> bool:
    """
    Inspects EC2/VPC security group IpPermissions for unrestricted ingress (0.0.0.0/0 or ::/0).
    Optionally matches against a specific target port (e.g. 22 for SSH, 3389 for RDP).
    """
    if not isinstance(permissions, list):
        return False

    for perm in permissions:
        if not isinstance(perm, dict):
            continue

        from_p = perm.get("FromPort")
        to_p = perm.get("ToPort")
        ip_proto = str(perm.get("IpProtocol", ""))

        port_ok = (
            target_port is None
            or ip_proto == "-1"
            or (from_p is not None and to_p is not None and int(from_p) <= int(target_port) <= int(to_p))
        )
        if not port_ok:
            continue

        # Check IPv4 0.0.0.0/0
        for rng in perm.get("IpRanges", []):
            if not isinstance(rng, dict):
                continue
            cidr = rng.get("CidrIp", "")
            if cidr == "0.0.0.0/0":
                return True
            if cidr:
                try:
                    if ipaddress.ip_network(cidr, strict=False).prefixlen == 0:
                        return True
                except ValueError:
                    pass

        # Check IPv6 ::/0
        for rng6 in perm.get("Ipv6Ranges", []):
            if not isinstance(rng6, dict):
                continue
            cidr6 = rng6.get("CidrIpv6", "")
            if cidr6 == "::/0":
                return True
            if cidr6:
                try:
                    if ipaddress.ip_network(cidr6, strict=False).prefixlen == 0:
                        return True
                except ValueError:
                    pass

    return False


def evaluate_condition(payload: Dict[str, Any], cond: ConditionRule) -> bool:
    """
    Evaluates a single field-level ConditionRule against a payload dictionary.
    Implements all 12 deterministic operators without any LLM calls.
    """
    val = extract_path(payload, cond.field_path)
    op = cond.operator

    if op == OperatorType.EXISTS:
        return (val is not None and val != "") == bool(cond.value)

    if op == OperatorType.EQ:
        return val == cond.value

    if op == OperatorType.NEQ:
        return val != cond.value

    if op == OperatorType.IN:
        if isinstance(val, list):
            return any(x in cond.value for x in val)
        return val in cond.value if cond.value is not None else False

    if op == OperatorType.NOT_IN:
        if isinstance(val, list):
            return all(x not in cond.value for x in val)
        return val not in cond.value if cond.value is not None else True

    if op == OperatorType.GTE:
        return val is not None and float(val) >= float(cond.value)

    if op == OperatorType.LTE:
        return val is not None and float(val) <= float(cond.value)

    if op == OperatorType.REGEX:
        return val is not None and bool(re.search(str(cond.value), str(val), re.IGNORECASE))

    if op == OperatorType.CIDR_OPEN_WORLD:
        return check_cidr_open_world(val, cond.value)

    if op == OperatorType.IAM_AST_WILDCARD:
        if isinstance(val, list):
            return any(check_iam_ast_wildcard(d, str(cond.value)) for d in val)
        return check_iam_ast_wildcard(val, str(cond.value))

    if op == OperatorType.KMS_CMK_ENCRYPTED:
        if not isinstance(val, dict):
            return False
        enc = bool(
            val.get("Encrypted")
            or val.get("StorageEncrypted")
            or val.get("KmsKeyId")
            or val.get("KMSMasterKeyId")
        )
        arn = str(val.get("KmsKeyId") or val.get("KMSMasterKeyId") or "")
        is_cmk = enc and arn.startswith("arn:aws:kms:") and ":alias/aws/" not in arn
        return is_cmk == bool(cond.value)

    if op == OperatorType.AGE_DAYS_GTE:
        if not val:
            return False
        try:
            dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            return ((now_utc - dt).total_seconds() / 86400.0) >= float(cond.value)
        except Exception:
            return False

    return False


def evaluate_rule(payload: Dict[str, Any], rule: DeterministicRuleSpec) -> bool:
    """
    Evaluates all conditions of a DeterministicRuleSpec against a resource or event payload.
    Supports match_logic: ALL (AND), ANY (OR), NONE (NOR).
    Returns True if matching conditions represent a VIOLATION (FAIL state).
    """
    if not rule.conditions:
        return False

    results = [evaluate_condition(payload, c) for c in rule.conditions]
    logic = str(rule.match_logic).upper()

    if logic == "ALL":
        return all(results)
    if logic == "ANY":
        return any(results)
    if logic == "NONE":
        return not any(results)

    return False


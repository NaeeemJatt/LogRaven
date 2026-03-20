#!/usr/bin/env python3
"""
sigma_to_lograven.py — Offline Sigma → LogRaven rule converter.

USAGE
-----
  python scripts/sigma_to_lograven.py \\
      --sigma-dir   /path/to/SigmaHQ/sigma/rules \\
      --output-dir  backend/app/data/rules/sigma_imported \\
      [--dry-run] [--verbose]

REQUIREMENTS
    pip install pyyaml

PURPOSE
    Recursively read Sigma YAML rule files from a SigmaHQ/sigma checkout,
    convert compatible rules to LogRaven YAML format, and write them into
    categorised output directories (by log_type).

LOGSOURCE MAPPING
    Sigma logsource → LogRaven log_type:
      product=windows, service=security   → windows_endpoint
      product=windows, service=system     → windows_endpoint
      product=windows, service=powershell → windows_endpoint
      product=windows, category=process_creation → windows_endpoint
      product=linux                       → linux_endpoint
      product=aws, service=cloudtrail     → cloudtrail
      category=webserver                  → web_server

FIELD MAPPING
    Sigma field → NormalizedEvent attribute or extra.<key>
    See FIELD_MAP below for full mapping.

CONDITIONS SUPPORTED
    Simple field modifiers: |contains, |startswith, |endswith, |re, |base64
    Multi-value lists:      field: [v1, v2, v3]  → contains_any
    Boolean AND / OR:       selection1 and selection2, selection1 or selection2
    NOT:                    not filter
    Simple keyword searches in raw_message

NOT SUPPORTED (rule is skipped with a warning)
    EQL/SIGMA query language (type: eql)
    Near / sequence conditions (multi-event state machines)
    Aggregate conditions:   count() by field > N  (use threshold type instead)
    Named pipe checks / Sysmon event_id 17/18
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
import uuid
from pathlib import Path

# Force UTF-8 stdout on Windows so rule titles/descriptions never hit cp1252 errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ── Logsource mapping ────────────────────────────────────────────────────────

def _logsource_to_log_type(logsource: dict) -> str | None:
    """
    Map a Sigma logsource dict to a LogRaven log_type string.
    Returns None for unsupported logsources.
    """
    if not logsource:
        return None

    product  = (logsource.get("product") or "").lower()
    service  = (logsource.get("service") or "").lower()
    category = (logsource.get("category") or "").lower()

    # AWS CloudTrail
    if product == "aws" and service == "cloudtrail":
        return "cloudtrail"

    # Web server
    if category == "webserver" or service in ("apache", "nginx", "iis"):
        return "web_server"

    # Linux
    if product == "linux":
        return "linux_endpoint"

    # Windows — all services and process_creation
    if product == "windows":
        if service in (
            "security", "system", "application", "powershell",
            "powershell-classic", "taskscheduler", "windefend",
            "sysmon", "dns-server",
        ) or category in (
            "process_creation", "network_connection", "registry_event",
            "registry_set", "registry_add", "file_event", "image_load",
            "pipe_created", "wmi_event", "create_remote_thread",
        ):
            return "windows_endpoint"

    return None


# ── Field mapping ─────────────────────────────────────────────────────────────

# Maps Sigma field names → LogRaven field paths.
# LogRaven fields without "extra." prefix are NormalizedEvent attributes.
# Fields prefixed with "extra." are stored in extra_fields.
FIELD_MAP: dict[str, str] = {
    # NormalizedEvent core fields
    "EventID":                "event_id",
    "EventId":                "event_id",
    "event_id":               "event_id",
    "ComputerName":           "hostname",
    "Computer":               "hostname",
    "Hostname":               "hostname",
    "WorkstationName":        "hostname",
    "SourceHostname":         "source_ip",
    "IpAddress":              "source_ip",
    "SourceIp":               "source_ip",
    "IpPort":                 "extra.IpPort",
    "User":                   "username",
    "SubjectUserName":        "username",
    "TargetUserName":         "username",
    "AccountName":            "username",
    # Windows EventData → extra.*
    "NewProcessName":             "extra.NewProcessName",
    "ProcessName":                "extra.NewProcessName",
    "OriginalFileName":           "extra.OriginalFileName",
    "CommandLine":                "extra.CommandLine",
    "ParentProcessName":          "extra.ParentProcessName",
    "ParentCommandLine":          "extra.ParentCommandLine",
    "ParentImage":                "extra.ParentProcessName",
    "Image":                      "extra.NewProcessName",
    "LogonType":                  "extra.LogonType",
    "AuthenticationPackageName":  "extra.AuthenticationPackageName",
    "PrivilegeList":               "extra.PrivilegeList",
    "PrivilegeName":               "extra.PrivilegeName",
    "TicketEncryptionType":        "extra.TicketEncryptionType",
    "TicketOptions":               "extra.TicketOptions",
    "Properties":                  "extra.Properties",
    "ObjectName":                  "extra.ObjectName",
    "ObjectType":                  "extra.ObjectType",
    "AccessMask":                  "extra.AccessMask",
    "ServiceName":                 "extra.ServiceName",
    "ServiceFileName":             "extra.ServiceFileName",
    "TaskName":                    "extra.TaskName",
    "TaskContent":                 "extra.TaskContent",
    "GroupName":                   "extra.GroupName",
    "ShareName":                   "extra.ShareName",
    "UserAccountControl":          "extra.UserAccountControl",
    "TargetObject":                "extra.TargetObject",
    "Details":                     "extra.Details",
    "EventType":                   "extra.EventType",
    "DestinationPort":             "extra.DestinationPort",
    "DestinationIp":               "destination_ip",
    "DestAddress":                 "destination_ip",
    # Linux syslog → extra.*
    "process":                "extra.process",
    "pid":                    "extra.pid",
    "msg":                    "extra.message",
    "message":                "extra.message",
    # CloudTrail → event_id / extra.*
    "eventName":              "event_id",
    "eventSource":            "extra.eventSource",
    "errorCode":              "extra.errorCode",
    "errorMessage":           "extra.errorMessage",
    "userAgent":              "extra.userAgent",
    "awsRegion":              "extra.awsRegion",
    # Nginx → extra.*
    "c-uri":                  "extra.request_path",
    "c-uri-stem":             "extra.request_path",
    "cs-uri-stem":            "extra.request_path",
    "c-useragent":            "extra.user_agent",
    "cs-user-agent":          "extra.user_agent",
    "cs-method":              "extra.method",
    "sc-status":              "extra.status_code",
    # Fallback — unknown fields → extra.*
}


def _map_field(sigma_field: str) -> str:
    """
    Return the LogRaven field path for a Sigma field name.
    Unknown fields are mapped to extra.<original_name>.
    """
    return FIELD_MAP.get(sigma_field, f"extra.{sigma_field}")


# ── Sigma modifier → LogRaven operator ───────────────────────────────────────

_MODIFIER_OP_MAP: dict[str, str] = {
    "contains":   "contains",
    "startswith": "startswith",
    "endswith":   "endswith",
    "re":         "re",
    "all":        "contains_all",  # field|contains|all
    "windash":    "contains",      # treats - and / equivalently
    "base64":     None,            # skip — complex
    "base64offset": None,          # skip
    "utf16le":    None,            # skip
    "utf16be":    None,            # skip
    "wide":       None,            # skip
    "cidr":       None,            # skip — CIDR not supported
    "lt":         None,
    "lte":        None,
    "gt":         None,
    "gte":        None,
}

_SEVERITY_MAP: dict[str, str] = {
    "informational": "informational",
    "low":           "low",
    "medium":        "medium",
    "high":          "high",
    "critical":      "critical",
}

_TACTIC_MAP: dict[str, str] = {
    "initial_access":         "initial-access",
    "execution":              "execution",
    "persistence":            "persistence",
    "privilege_escalation":   "privilege-escalation",
    "defense_evasion":        "defense-evasion",
    "credential_access":      "credential-access",
    "discovery":              "discovery",
    "lateral_movement":       "lateral-movement",
    "collection":             "collection",
    "command_and_control":    "command-and-control",
    "exfiltration":           "exfiltration",
    "impact":                 "impact",
    "resource_development":   "resource-development",
    "reconnaissance":         "reconnaissance",
}


# ── YAML detection parsing ────────────────────────────────────────────────────

class SkipRule(Exception):
    """Raised when a rule cannot be converted."""


def _parse_field_value(
    sigma_field: str,
    raw_field_name: str,
    values: list[str],
    modifiers: list[str],
) -> list[dict] | None:
    """
    Convert a Sigma field with its modifiers and values into a list of
    LogRaven SimpleCondition dicts.
    Returns None if conversion is not possible.
    """
    lr_field = _map_field(sigma_field)

    # Unsupported modifiers
    for mod in modifiers:
        if mod in _MODIFIER_OP_MAP and _MODIFIER_OP_MAP[mod] is None:
            return None  # skip this field

    # Determine operator
    if not modifiers or modifiers == ["contains"]:
        op = "contains"
    elif modifiers[-1] == "startswith":
        op = "startswith"
    elif modifiers[-1] == "endswith":
        op = "endswith"
    elif modifiers[-1] == "re":
        op = "re"
    elif "all" in modifiers:
        op = "contains_all"
    else:
        op = "contains"

    # Null check
    null_vals = [v for v in values if v is None or str(v).lower() == "null"]
    real_vals = [str(v) for v in values if v is not None and str(v).lower() != "null"]

    conditions: list[dict] = []

    if null_vals:
        # Check field does not exist
        conditions.append({"field": lr_field, "op": "not_exists"})

    if real_vals:
        if op in ("contains_all",):
            conditions.append({"field": lr_field, "op": op, "values": real_vals})
        elif len(real_vals) == 1:
            conditions.append({"field": lr_field, "op": op, "value": real_vals[0]})
        else:
            # Multiple values → contains_any (OR semantics)
            if op in ("startswith", "endswith"):
                # Sigma startswith/endswith|all uses OR logic per value
                conditions.append({"field": lr_field, "op": "contains_any", "values": real_vals})
            else:
                conditions.append({"field": lr_field, "op": "contains_any", "values": real_vals})

    return conditions if conditions else None


def _parse_sigma_value(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return str(v).lower()
    return str(v)


def _parse_selection(selection_dict: dict) -> list[dict]:
    """
    Parse a Sigma detection selection dict into a list of LogRaven condition dicts.
    Each key in the selection is AND-ed; multiple values for a key are OR-ed.
    """
    conditions: list[dict] = []

    for key, raw_value in selection_dict.items():
        # Parse field|modifier1|modifier2
        parts = key.split("|")
        sigma_field = parts[0]
        modifiers = parts[1:] if len(parts) > 1 else []

        # Normalise values to a list
        if raw_value is None:
            values = [None]
        elif isinstance(raw_value, list):
            values = raw_value
        else:
            values = [raw_value]

        parsed = _parse_field_value(sigma_field, key, values, modifiers)
        if parsed is None:
            raise SkipRule(f"Cannot convert field: {key!r}")
        conditions.extend(parsed)

    return conditions


def _flatten_to_or(nested: list[list[dict]]) -> list[dict]:
    """Flatten a list of condition-lists by or-ing them (pick the first non-empty group)."""
    for group in nested:
        if group:
            return group
    return []


def _parse_condition_expr(
    expr: str,
    named_selections: dict[str, list[dict]],
    named_filters:    dict[str, list[dict]],
) -> tuple[list[dict], str]:
    """
    Parse a Sigma condition expression.
    Supported patterns:
      selection
      selection and not filter
      1 of selection*
      all of selection*
      keywords
    Returns (conditions, condition_logic).
    """
    # Normalise whitespace
    expr = re.sub(r"\s+", " ", expr.strip()).lower()

    # Keyword-only rule (unquoted keywords)
    if expr == "keywords":
        return [], "and"  # caller handles separately

    # Single selection with optional NOT filter
    # Patterns: "selection", "selection and not filter",
    #           "selection and (not filter1 and not filter2)"
    m = re.match(r"^(\w+)(?:\s+and\s+not\s+(\w+))?$", expr)
    if m:
        sel_name = m.group(1)
        flt_name = m.group(2)
        conds = list(named_selections.get(sel_name, []))
        if flt_name and flt_name in named_filters:
            for c in named_filters[flt_name]:
                negated = dict(c)
                negated["negate"] = True
                conds.append(negated)
        return conds, "and"

    # "1 of selection*" — OR any matching selection group
    m = re.match(r"^1\s+of\s+(\w+)\*$", expr)
    if m:
        prefix = m.group(1).rstrip("*")
        all_conds: list[dict] = []
        for name, conds in named_selections.items():
            if name.startswith(prefix):
                all_conds.extend(conds)
        return all_conds, "or"

    # "all of selection*" — AND all matching selection groups
    m = re.match(r"^all\s+of\s+(\w+)\*$", expr)
    if m:
        prefix = m.group(1).rstrip("*")
        all_conds: list[dict] = []
        for name, conds in named_selections.items():
            if name.startswith(prefix):
                all_conds.extend(conds)
        return all_conds, "and"

    # "selection1 or selection2"
    if " or " in expr:
        parts = [p.strip() for p in re.split(r"\bor\b", expr)]
        all_conds = []
        for part in parts:
            conds = named_selections.get(part, [])
            all_conds.extend(conds)
        return all_conds, "or"

    # "selection1 and selection2"
    if " and " in expr:
        parts = [p.strip() for p in re.split(r"\band\b", expr)]
        all_conds = []
        for part in parts:
            all_conds.extend(named_selections.get(part, []))
        return all_conds, "and"

    # Single named selection
    if expr in named_selections:
        return named_selections[expr], "and"

    raise SkipRule(f"Unsupported condition expression: {expr!r}")


# ── MITRE tag extraction ──────────────────────────────────────────────────────

def _extract_mitre(tags: list[str]) -> tuple[str | None, str | None]:
    technique_id = None
    tactic = None
    for tag in tags:
        tag_lower = tag.lower()
        # technique IDs: attack.t1234 / attack.t1234.001
        m = re.match(r"attack\.(t\d{4}(?:\.\d{3})?)", tag_lower)
        if m and technique_id is None:
            technique_id = m.group(1).upper()
        # tactics: attack.initial_access etc.
        if tag_lower.startswith("attack.") and not re.match(r"attack\.t\d{4}", tag_lower):
            tactic_raw = tag_lower.replace("attack.", "").replace("-", "_")
            tactic = _TACTIC_MAP.get(tactic_raw)
    return technique_id, tactic


# ── Flag derivation ───────────────────────────────────────────────────────────

def _derive_flag(technique_id: str | None, tactic: str | None, title: str) -> str | None:
    if not technique_id and not tactic:
        return None
    t = (tactic or "").lower()
    if t in ("credential-access",):
        return "credential_access"
    if t in ("privilege-escalation",):
        return "privilege_escalation"
    if t in ("defense-evasion",):
        return "log_tampering"
    if t in ("persistence",):
        return "persistence_mechanism"
    if t in ("lateral-movement",):
        return "lateral_movement_candidate"
    if t in ("discovery", "reconnaissance"):
        return "recon_candidate"
    if t in ("collection", "exfiltration"):
        return "data_exfil_candidate"
    if t in ("execution",):
        return "suspicious_process"
    if t in ("initial-access",):
        return "injection_attempt"
    if t in ("impact",):
        return "suspicious_process"
    return None


# ── Rule conversion ───────────────────────────────────────────────────────────

def convert_rule(sigma_rule: dict) -> dict | None:
    """
    Convert a single Sigma rule dict to a LogRaven rule dict.
    Returns None if the rule should be skipped.
    """
    try:
        status = (sigma_rule.get("status") or "").lower()
        if status in ("deprecated", "unsupported"):
            return None

        logsource = sigma_rule.get("logsource") or {}
        log_type  = _logsource_to_log_type(logsource)
        if log_type is None:
            return None

        detection = sigma_rule.get("detection") or {}
        if not detection:
            return None

        condition_expr = detection.get("condition") or ""
        if isinstance(condition_expr, list):
            condition_expr = condition_expr[0]  # use first
        condition_expr = str(condition_expr)

        # Reject complex unsupported patterns
        for unsupported in (
            "count(", "sum(", "min(", "max(", "avg(",
            "near ", "| ", "->",
        ):
            if unsupported in condition_expr.lower():
                return None

        # Parse named selections and filters
        named_selections: dict[str, list[dict]] = {}
        named_filters:    dict[str, list[dict]] = {}
        keywords_list:    list[str]             = []

        for name, value in detection.items():
            if name == "condition":
                continue
            if name == "keywords":
                if isinstance(value, list):
                    keywords_list = [str(v) for v in value]
                continue
            if name.startswith("filter"):
                # Store as negative conditions
                if isinstance(value, dict):
                    try:
                        named_filters[name] = _parse_selection(value)
                    except SkipRule:
                        return None
                continue
            # Named selection
            if isinstance(value, dict):
                try:
                    named_selections[name] = _parse_selection(value)
                except SkipRule:
                    return None
            elif isinstance(value, list):
                # List of dicts = OR-grouped selections
                all_conds: list[dict] = []
                for item in value:
                    if isinstance(item, dict):
                        try:
                            all_conds.extend(_parse_selection(item))
                        except SkipRule:
                            return None
                    else:
                        # Plain string → raw_message contains
                        all_conds.append({
                            "field": "raw_message",
                            "op": "contains",
                            "value": str(item),
                        })
                named_selections[name] = all_conds

        # Handle keywords-only rule
        if condition_expr.strip().lower() == "keywords" and keywords_list:
            conditions = [
                {"field": "raw_message", "op": "contains", "value": kw}
                for kw in keywords_list
            ]
            logic = "or"
        else:
            try:
                conditions, logic = _parse_condition_expr(
                    condition_expr, named_selections, named_filters
                )
            except SkipRule:
                return None

        if not conditions:
            return None

        # Metadata
        title  = str(sigma_rule.get("title") or "Untitled")
        level  = (sigma_rule.get("level") or "medium").lower()
        tags   = sigma_rule.get("tags") or []
        desc   = str(sigma_rule.get("description") or "")

        severity        = _SEVERITY_MAP.get(level, "medium")
        technique_id, tactic = _extract_mitre(tags)
        flag            = _derive_flag(technique_id, tactic, title)

        rule_id = f"lr-sigma-imported-{str(uuid.uuid4())[:8]}"

        lr_rule: dict = {
            "id":          rule_id,
            "title":       title,
            "source":      "sigma",
            "log_type":    log_type,
            "severity":    severity,
            "description": textwrap.shorten(desc, 200) if desc else "",
            "enabled":     True,
            "requires_sysmon": False,
            "match": {
                "type":            "simple",
                "log_type":        log_type,
                "conditions":      conditions,
                "condition_logic": logic,
            },
        }
        if technique_id:
            lr_rule["mitre_technique_id"] = technique_id
        if tactic:
            lr_rule["mitre_tactic"] = tactic
        if flag:
            lr_rule["flag"] = flag

        return lr_rule

    except Exception:
        return None


# ── File walker ───────────────────────────────────────────────────────────────

def convert_directory(
    sigma_dir:  Path,
    output_dir: Path,
    dry_run:    bool = False,
    verbose:    bool = False,
) -> tuple[int, int, int]:
    """
    Walk sigma_dir recursively, convert rules, write to output_dir/<log_type>/.
    Returns (total, converted, skipped) counts.
    """
    total = converted = skipped = 0
    buckets: dict[str, list[dict]] = {}

    for path in sorted(sigma_dir.rglob("*.yml")):
        total += 1
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                sigma_rule = yaml.safe_load(fh)
        except Exception as exc:
            if verbose:
                print(f"  SKIP (parse error) {path.name}: {exc}")
            skipped += 1
            continue

        if not isinstance(sigma_rule, dict):
            skipped += 1
            continue

        lr_rule = convert_rule(sigma_rule)
        if lr_rule is None:
            skipped += 1
            if verbose:
                print(f"  SKIP {path.name}")
            continue

        log_type = lr_rule["log_type"]
        buckets.setdefault(log_type, []).append(lr_rule)
        converted += 1
        if verbose:
                print(f"  OK   {path.name} -> {log_type}")

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for log_type, rules in buckets.items():
            out_path = output_dir / f"{log_type}.yaml"
            with open(out_path, "w", encoding="utf-8") as fh:
                yaml.dump({"rules": rules}, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"  Wrote {len(rules):4d} rules -> {out_path}")

    return total, converted, skipped


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sigma-dir", required=True,
        help="Path to SigmaHQ/sigma/rules directory (cloned from GitHub).",
    )
    parser.add_argument(
        "--output-dir",
        default="backend/app/data/rules/sigma_imported",
        help="Where to write the generated LogRaven YAML files.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and report; do not write files.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-rule status.")
    args = parser.parse_args()

    sigma_dir  = Path(args.sigma_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser()

    if not sigma_dir.exists():
        print(f"ERROR: Sigma directory not found: {sigma_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSigma source : {sigma_dir}")
    print(f"Output dir   : {output_dir}")
    print(f"Dry run      : {args.dry_run}")
    print()

    total, converted, skipped = convert_directory(
        sigma_dir, output_dir, dry_run=args.dry_run, verbose=args.verbose,
    )

    print()
    print(f"Total rules  : {total:5d}")
    print(f"Converted    : {converted:5d}  ({100*converted//max(total,1)}%)")
    print(f"Skipped      : {skipped:5d}")
    if not args.dry_run and converted:
        print(f"\nRules written to: {output_dir}")
        print("Next step: restart the backend — loader picks up new files automatically.")


if __name__ == "__main__":
    main()

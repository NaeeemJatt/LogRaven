# LogRaven — Rule Loader
# Reads YAML rule files from app/data/rules/ and returns RuleDefinition objects.
# Rules are cached after the first load; call reload_rules() to force a refresh.

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from app.rules.schema import RuleDefinition, SimpleMatch, ThresholdMatch
from app.utils.logger import get_logger

logger = get_logger("lograven.rules")

RULES_DIR: Path = Path(__file__).parent.parent / "data" / "rules"

_RULES: Optional[list[RuleDefinition]] = None


def _parse_match(match_dict: dict) -> SimpleMatch | ThresholdMatch:
    match_type = match_dict.get("type")
    if match_type == "simple":
        return SimpleMatch(**match_dict)
    if match_type == "threshold":
        return ThresholdMatch(**match_dict)
    raise ValueError(f"Unknown match type: {match_type!r}")


def _load_rule_file(path: Path) -> list[RuleDefinition]:
    """Parse a single YAML file into RuleDefinition objects."""
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if data is None:
        return []

    # Accept three formats:
    #   { rules: [...] }   — recommended multi-rule file
    #   { id: ..., ... }   — single rule at top level
    #   [ {...}, {...} ]   — bare list
    if isinstance(data, dict) and "rules" in data:
        rule_list = data["rules"]
    elif isinstance(data, dict):
        rule_list = [data]
    elif isinstance(data, list):
        rule_list = data
    else:
        return []

    results: list[RuleDefinition] = []
    for rule_data in rule_list:
        if not isinstance(rule_data, dict):
            continue
        try:
            raw = dict(rule_data)
            match_raw = raw.pop("match", {})
            match_obj = _parse_match(match_raw)
            rule = RuleDefinition(**raw, match=match_obj)
            if rule.enabled and not rule.requires_sysmon:
                results.append(rule)
        except Exception as exc:
            logger.warning("Skipped rule in %s: %s", path.name, exc)
    return results


def load_rules(rules_dir: Path = RULES_DIR) -> list[RuleDefinition]:
    """Load all YAML rules from *rules_dir* (recursive)."""
    rules: list[RuleDefinition] = []
    if not rules_dir.exists():
        logger.warning("Rules directory not found: %s", rules_dir)
        return rules

    for path in sorted(rules_dir.rglob("*.yaml")):
        try:
            loaded = _load_rule_file(path)
            rules.extend(loaded)
        except Exception as exc:
            logger.warning("Failed to load rule file %s: %s", path.name, exc)

    simple_count    = sum(1 for r in rules if isinstance(r.match, SimpleMatch))
    threshold_count = sum(1 for r in rules if isinstance(r.match, ThresholdMatch))
    logger.info(
        "Rules loaded: %d total (%d simple, %d threshold) from %s",
        len(rules), simple_count, threshold_count, rules_dir,
    )
    return rules


def get_rules() -> list[RuleDefinition]:
    """Return cached rules, loading from disk on first call."""
    global _RULES
    if _RULES is None:
        _RULES = load_rules()
    return _RULES


def reload_rules() -> list[RuleDefinition]:
    """Force reload from disk — used in development / hot-reload."""
    global _RULES
    _RULES = None
    return get_rules()

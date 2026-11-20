# LogRaven — Rule Loader (Unified Loader for CSPM & Detection Rules)
# Reads YAML rule files from app/data/rules/ and manages:
# 1. DeterministicRuleSpec instances indexed by ID, CID, and (Provider, Service, TargetSource)
# 2. RuleDefinition objects for standard log-stream event detection

from __future__ import annotations

import glob
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.rules.schema import (
    DeterministicRuleSpec,
    RuleDefinition,
    SimpleMatch,
    ThresholdMatch,
)
from app.utils.logger import get_logger

logger = get_logger("lograven.rules")

RULES_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "rules"

_RULES: Optional[list[RuleDefinition]] = None
_DEFAULT_LOADER: Optional[RuleLoader] = None


class RuleLoader:
    """Hot-reloadable multi-dimensional indexed loader for Deterministic CSPM & Log rules."""

    def __init__(self, rules_dir: Optional[str | Path] = None):
        self.rules_dir = Path(rules_dir) if rules_dir else RULES_DIR
        self.rules_by_id: Dict[str, DeterministicRuleSpec] = {}
        self.rules_by_cid: Dict[str, DeterministicRuleSpec] = {}
        self.index_by_target: Dict[Tuple[str, str, str], List[DeterministicRuleSpec]] = defaultdict(list)
        self.detection_rules: List[RuleDefinition] = []

    def load_all(self) -> int:
        """Loads and indexes all YAML rules from rules_dir."""
        self.rules_by_id.clear()
        self.rules_by_cid.clear()
        self.index_by_target.clear()
        self.detection_rules.clear()

        if not self.rules_dir.exists():
            logger.warning("Rules directory does not exist: %s", self.rules_dir)
            return 0

        # Scan all .yaml files in rules_dir root (cspm_*.yaml, cloudtrail.yaml, etc.)
        yaml_paths = sorted(self.rules_dir.glob("*.yaml"))

        for path in yaml_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    doc = yaml.safe_load(f) or {}

                rule_list = doc.get("rules", []) if isinstance(doc, dict) else (doc if isinstance(doc, list) else [])
                if isinstance(doc, dict) and not rule_list and ("id" in doc or "rule_id" in doc):
                    rule_list = [doc]

                for raw_rule in rule_list:
                    if not isinstance(raw_rule, dict):
                        continue

                    # Check if it's a Deterministic CSPM / Log rule
                    if "rule_id" in raw_rule:
                        try:
                            spec = DeterministicRuleSpec(**raw_rule)
                            self.rules_by_id[spec.rule_id] = spec
                            if spec.cid:
                                self.rules_by_cid[str(spec.cid)] = spec
                            key = (spec.provider.upper(), spec.service.upper(), spec.target_source)
                            self.index_by_target[key].append(spec)
                        except Exception as exc:
                            logger.warning("Failed to parse DeterministicRuleSpec in %s: %s", path.name, exc)

                    # Check if it's a standard Detection Rule
                    elif "id" in raw_rule and "match" in raw_rule:
                        try:
                            raw = dict(raw_rule)
                            match_raw = raw.pop("match", {})
                            match_obj = _parse_match(match_raw)
                            r_def = RuleDefinition(**raw, match=match_obj)
                            if r_def.enabled and not r_def.requires_sysmon:
                                self.detection_rules.append(r_def)
                        except Exception as exc:
                            logger.warning("Failed to parse RuleDefinition in %s: %s", path.name, exc)

            except Exception as exc:
                logger.warning("Error reading rule file %s: %s", path.name, exc)

        logger.info(
            "RuleLoader loaded %d deterministic rules (%d CIDs) and %d detection rules from %s",
            len(self.rules_by_id),
            len(self.rules_by_cid),
            len(self.detection_rules),
            self.rules_dir,
        )
        return len(self.rules_by_id)

    def get_rules_for_service(
        self, provider: str, service: str, target_source: Optional[str] = None
    ) -> List[DeterministicRuleSpec]:
        """Fetch all deterministic rules for a specific provider, service, and target source."""
        if target_source is None or (target_source == "aws_config_state" and provider.upper() != "AWS"):
            target_source = {
                "AWS": "aws_config_state",
                "AZURE": "azure_resource_graph",
                "GCP": "gcp_asset_inventory",
                "OCI": "oci_cloud_guard",
            }.get(provider.upper(), target_source or "aws_config_state")
        return self.index_by_target.get((provider.upper(), service.upper(), target_source), [])

    def get_log_rules(self, provider: str = "AWS") -> List[DeterministicRuleSpec]:
        """Fetch all rules configured for log stream evaluation."""
        out = []
        prov_upper = provider.upper()
        for (prov, _svc, src), rules in self.index_by_target.items():
            if prov == prov_upper and src.endswith("_log"):
                out.extend(rules)
        return out

    def get_rule_by_cid(self, cid: str | int) -> Optional[DeterministicRuleSpec]:
        """Fetch rule by Qualys CID."""
        return self.rules_by_cid.get(str(cid))

    def get_rule_by_id(self, rule_id: str) -> Optional[DeterministicRuleSpec]:
        """Fetch rule by unique rule_id."""
        return self.rules_by_id.get(rule_id)


# ── Standalone Functions for Backward Compatibility ───────────────────────────

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
        if not isinstance(rule_data, dict) or "match" not in rule_data:
            continue
        try:
            raw = dict(rule_data)
            match_raw = raw.pop("match", {})
            match_obj = _parse_match(match_raw)
            rule = RuleDefinition(**raw, match=match_obj)
            if rule.enabled and not rule.requires_sysmon:
                results.append(rule)
        except Exception as exc:
            logger.warning("Skipped detection rule in %s: %s", path.name, exc)
    return results


def load_rules(rules_dir: Path = RULES_DIR) -> list[RuleDefinition]:
    """Load all YAML detection rules from rules_dir (recursive)."""
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

    simple_count = sum(1 for r in rules if isinstance(r.match, SimpleMatch))
    threshold_count = sum(1 for r in rules if isinstance(r.match, ThresholdMatch))
    logger.info(
        "Rules loaded: %d total (%d simple, %d threshold) from %s",
        len(rules), simple_count, threshold_count, rules_dir,
    )
    return rules


def get_rules() -> list[RuleDefinition]:
    """Return cached detection rules, loading from disk on first call."""
    global _RULES
    if _RULES is None:
        _RULES = load_rules()
    return _RULES


def reload_rules() -> list[RuleDefinition]:
    """Force reload from disk — used in development / hot-reload."""
    global _RULES, _DEFAULT_LOADER
    _RULES = load_rules()
    if _DEFAULT_LOADER is not None:
        _DEFAULT_LOADER.load_all()
    return _RULES


def get_default_rule_loader() -> RuleLoader:
    """Return singleton instance of RuleLoader."""
    global _DEFAULT_LOADER
    if _DEFAULT_LOADER is None:
        _DEFAULT_LOADER = RuleLoader()
        _DEFAULT_LOADER.load_all()
    return _DEFAULT_LOADER

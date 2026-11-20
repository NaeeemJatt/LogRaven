# LogRaven — Compliance Framework Registry (base types)
#
# A Framework is a content pack: an ordered list of Controls, each mapped to the
# normalized evidence "signals" that are relevant to grading it. The grading
# engine is framework-agnostic — it reads controls + signals from the registry,
# so adding a new framework is pure data (a new pack module), no engine changes.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    """A single compliance control within a framework."""

    control_id: str                     # e.g. "CC6.1", "A.8.5", "1.4", "164.312(a)(1)"
    name: str
    category: str = "General"           # grouping for UI / PDF sections
    signals: tuple[str, ...] = ()        # relevant evidence signal keys (see signals.py)
    automatable: bool = True            # False => needs manual evidence (policy, training, HR)
    guidance: str = ""                  # short remediation hint shown on FAIL/PARTIAL

    def as_prompt_dict(self) -> dict[str, str]:
        return {"control_id": self.control_id, "control_name": self.name}


@dataclass(frozen=True)
class Framework:
    """A compliance framework / standard (content pack)."""

    id: str                              # stable slug: "soc2", "iso27001", "cis_aws"
    name: str                            # display name: "SOC 2 Type II"
    version: str
    description: str
    controls: tuple[Control, ...]

    @property
    def automatable_controls(self) -> tuple[Control, ...]:
        return tuple(c for c in self.controls if c.automatable)

    @property
    def automatable_count(self) -> int:
        return len(self.automatable_controls)

    def control_ids(self) -> set[str]:
        return {c.control_id for c in self.controls}

    def get_control(self, control_id: str) -> Control | None:
        for control in self.controls:
            if control.control_id == control_id:
                return control
        return None


import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY: dict[str, Framework] = {}
POLICY_REGISTRY: dict[str, dict[str, Any]] = {}
MANDATE_REGISTRY: dict[str, dict[str, Any]] = {}


def register(framework: Framework) -> None:
    """Register (or replace) a framework in the global registry."""
    REGISTRY[framework.id] = framework


def get_framework(framework_id: str) -> Framework:
    try:
        return REGISTRY[framework_id]
    except KeyError as exc:
        raise KeyError(f"Unknown compliance framework: {framework_id!r}") from exc


def list_frameworks() -> list[Framework]:
    return sorted(REGISTRY.values(), key=lambda f: f.name)


def is_registered(framework_id: str) -> bool:
    return framework_id in REGISTRY


# ── Policy & Mandate Catalog Registries (FR-DET-07) ───────────────────────────

def load_policies_and_mandates_catalog(catalog_dir: Optional[Path | str] = None) -> None:
    """Load the 29 Policies and 38 Mandates from the canonical CSV catalog."""
    cat_dir = Path(catalog_dir) if catalog_dir else Path(__file__).resolve().parent.parent.parent / "data" / "csv_catalog"
    pol_path = cat_dir / "policies.csv"
    mand_path = cat_dir / "mandates.csv"

    if pol_path.is_file():
        with open(pol_path, "r", encoding="utf-8", errors="replace") as f:
            rows = list(csv.reader(f))
        for idx, r in enumerate(rows[:10]):
            if r and r[0].strip().upper() == "POLICY TITLE":
                headers = [c.strip() for c in r]
                for data_row in rows[idx + 1:]:
                    if len(data_row) == len(headers) and any(c.strip() for c in data_row):
                        entry = dict(zip(headers, [c.strip() for c in data_row]))
                        POLICY_REGISTRY[entry["POLICY TITLE"]] = entry
                break

    if mand_path.is_file():
        with open(mand_path, "r", encoding="utf-8", errors="replace") as f:
            rows = list(csv.reader(f))
        for idx, r in enumerate(rows[:10]):
            if r and r[0].strip().upper() == "NAME":
                headers = [c.strip() for c in r]
                for data_row in rows[idx + 1:]:
                    if len(data_row) == len(headers) and any(c.strip() for c in data_row):
                        entry = dict(zip(headers, [c.strip() for c in data_row]))
                        MANDATE_REGISTRY[entry["NAME"]] = entry
                break


def get_policy(title: str) -> Optional[dict[str, Any]]:
    if not POLICY_REGISTRY:
        load_policies_and_mandates_catalog()
    if title in POLICY_REGISTRY:
        return POLICY_REGISTRY[title]
    tl = title.lower()
    for pol_title, data in POLICY_REGISTRY.items():
        if tl in pol_title.lower():
            return data
    return None


def get_mandate(name: str) -> Optional[dict[str, Any]]:
    if not MANDATE_REGISTRY:
        load_policies_and_mandates_catalog()
    if name in MANDATE_REGISTRY:
        return MANDATE_REGISTRY[name]
    nl = name.lower()
    for mand_name, data in MANDATE_REGISTRY.items():
        if nl in mand_name.lower():
            return data
    return None


def list_policies() -> list[dict[str, Any]]:
    if not POLICY_REGISTRY:
        load_policies_and_mandates_catalog()
    return list(POLICY_REGISTRY.values())


def list_mandates() -> list[dict[str, Any]]:
    if not MANDATE_REGISTRY:
        load_policies_and_mandates_catalog()
    return list(MANDATE_REGISTRY.values())

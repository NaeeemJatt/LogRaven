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


REGISTRY: dict[str, Framework] = {}


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

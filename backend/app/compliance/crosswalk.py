# LogRaven — Compliance control crosswalk
#
# Computes, from the framework registry, which controls across frameworks rely
# on each evidence signal. This powers the "collect once, satisfy many" crosswalk
# view and the shared-control reuse metric on the posture dashboard.

from __future__ import annotations

from typing import Any

from app.compliance.frameworks import list_frameworks
from app.compliance.signals import SIGNAL_CATALOG


def build_crosswalk(framework_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """
    For each evidence signal, list the (framework, control) pairs that use it.

    Returns rows sorted by how many frameworks share the signal (most-shared first),
    so the UI can highlight the highest-leverage evidence.
    """
    frameworks = list_frameworks()
    if framework_ids:
        wanted = set(framework_ids)
        frameworks = [f for f in frameworks if f.id in wanted]

    rows: list[dict[str, Any]] = []
    for signal_key, description in SIGNAL_CATALOG.items():
        controls: list[dict[str, str]] = []
        frameworks_hit: set[str] = set()
        for framework in frameworks:
            for control in framework.controls:
                if signal_key in control.signals:
                    controls.append(
                        {
                            "framework_id": framework.id,
                            "framework_name": framework.name,
                            "control_id": control.control_id,
                            "control_name": control.name,
                        }
                    )
                    frameworks_hit.add(framework.id)
        if controls:
            rows.append(
                {
                    "signal": signal_key,
                    "description": description,
                    "framework_count": len(frameworks_hit),
                    "control_count": len(controls),
                    "controls": controls,
                }
            )

    rows.sort(key=lambda r: (r["framework_count"], r["control_count"]), reverse=True)
    return rows


def reuse_factor(framework_ids: list[str]) -> float:
    """
    Evidence reuse factor: total control->signal references divided by the number
    of distinct signals used. >1 means a single piece of evidence is reused across
    multiple controls/frameworks (the core value of collect-once, map-to-many).
    """
    frameworks = [f for f in list_frameworks() if f.id in set(framework_ids)]
    total_refs = 0
    used_signals: set[str] = set()
    for framework in frameworks:
        for control in framework.controls:
            for signal in control.signals:
                total_refs += 1
                used_signals.add(signal)
    if not used_signals:
        return 0.0
    return round(total_refs / len(used_signals), 2)

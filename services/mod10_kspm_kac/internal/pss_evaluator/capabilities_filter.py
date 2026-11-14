"""Linux Capabilities Filter & Audit (PRD-MOD-10).

Verifies container specifications drop ALL capabilities and flags dangerous additions.
"""

from typing import Any, Dict, List, Set

DANGEROUS_CAPS: Set[str] = {
    "SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "DAC_OVERRIDE", "SYS_RAWIO",
    "SYS_CHROOT", "SYS_BOOT", "KILL", "CHOWN"
}


class CapabilitiesFilter:
    """Audits Linux capabilities added or dropped on containers."""

    @classmethod
    def evaluate_pod_spec(cls, pod_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        all_containers: List[Dict[str, Any]] = []
        all_containers.extend(pod_spec.get("containers", []))
        all_containers.extend(pod_spec.get("initContainers", []))
        all_containers.extend(pod_spec.get("ephemeralContainers", []))

        for c in all_containers:
            c_name = c.get("name", "unknown")
            sc = c.get("securityContext", {}) or {}
            caps = sc.get("capabilities", {}) or {}

            added = [str(x).upper() for x in caps.get("add", [])]
            dropped = [str(x).upper() for x in caps.get("drop", [])]

            # Flag dangerous additions
            for cap in added:
                clean_cap = cap.replace("CAP_", "")
                if clean_cap in DANGEROUS_CAPS:
                    findings.append({
                        "rule_id": f"K8S_DANGEROUS_CAP_{clean_cap}",
                        "severity": "HIGH",
                        "container": c_name,
                        "message": f"Container '{c_name}' adds dangerous capability CAP_{clean_cap}.",
                    })

            # Check if ALL is dropped (PSS Restricted profile requirement)
            if "ALL" not in dropped:
                findings.append({
                    "rule_id": "K8S_CAPABILITIES_NOT_DROPPED_ALL",
                    "severity": "LOW",
                    "container": c_name,
                    "message": f"Container '{c_name}' does not drop ALL capabilities.",
                })

        return findings

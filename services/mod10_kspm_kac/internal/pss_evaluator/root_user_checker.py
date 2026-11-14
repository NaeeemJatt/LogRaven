"""Root User Execution Checker (PRD-MOD-10).

Enforces CIS Kubernetes Benchmark guidelines regarding non-root execution.
"""

from typing import Any, Dict, List


class RootUserChecker:
    """Audits container specifications to ensure workloads do not execute as root (UID 0)."""

    @classmethod
    def evaluate_pod_spec(cls, pod_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        pod_sc = pod_spec.get("securityContext", {}) or {}
        pod_run_as_non_root = pod_sc.get("runAsNonRoot")

        all_containers: List[Dict[str, Any]] = []
        all_containers.extend(pod_spec.get("containers", []))
        all_containers.extend(pod_spec.get("initContainers", []))
        all_containers.extend(pod_spec.get("ephemeralContainers", []))

        for c in all_containers:
            c_name = c.get("name", "unknown")
            c_sc = c.get("securityContext", {}) or {}

            # Specific container check overrides pod level
            c_non_root = c_sc.get("runAsNonRoot")
            c_user = c_sc.get("runAsUser")

            if c_user == 0:
                findings.append({
                    "rule_id": "K8S_CONTAINER_RUNS_AS_ROOT",
                    "severity": "HIGH",
                    "container": c_name,
                    "message": f"Container '{c_name}' explicitly configured with runAsUser: 0 (root).",
                })
            elif c_non_root is False or (c_non_root is None and pod_run_as_non_root is not True):
                findings.append({
                    "rule_id": "K8S_CONTAINER_ROOT_ALLOWED",
                    "severity": "MEDIUM",
                    "container": c_name,
                    "message": f"Container '{c_name}' does not enforce runAsNonRoot: true.",
                })

        return findings

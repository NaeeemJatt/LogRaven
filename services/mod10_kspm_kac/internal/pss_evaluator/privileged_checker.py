"""Pod Security Standards (PSS) Privileged & Host Namespace Checker (PRD-MOD-10 / TC-MOD10-001)."""

from typing import Any, Dict, List


class PrivilegedChecker:
    """Evaluates container and pod securityContext against CIS K8s Benchmark and PSS."""

    @classmethod
    def evaluate_pod_spec(cls, pod_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Audits a pod spec (or pod template spec) for privileged execution and host namespaces."""
        findings: List[Dict[str, Any]] = []

        # 1. Pod-level host namespaces
        if pod_spec.get("hostPID") is True:
            findings.append({
                "rule_id": "K8S_HOST_PID",
                "severity": "HIGH",
                "message": "Sharing host PID namespace is prohibited by LogRaven KSPM policy.",
            })

        if pod_spec.get("hostNetwork") is True:
            findings.append({
                "rule_id": "K8S_HOST_NETWORK",
                "severity": "HIGH",
                "message": "Sharing host network namespace is prohibited by LogRaven KSPM policy.",
            })

        if pod_spec.get("hostIPC") is True:
            findings.append({
                "rule_id": "K8S_HOST_IPC",
                "severity": "HIGH",
                "message": "Sharing host IPC namespace is prohibited by LogRaven KSPM policy.",
            })

        # 2. Container-level privileged checks (containers + initContainers + ephemeralContainers)
        all_containers: List[Dict[str, Any]] = []
        all_containers.extend(pod_spec.get("containers", []))
        all_containers.extend(pod_spec.get("initContainers", []))
        all_containers.extend(pod_spec.get("ephemeralContainers", []))

        for c in all_containers:
            c_name = c.get("name", "unknown")
            sc = c.get("securityContext", {}) or {}

            # Privileged mode
            if sc.get("privileged") is True:
                findings.append({
                    "rule_id": "K8S_PRIVILEGED_CONTAINER",
                    "severity": "CRITICAL",
                    "container": c_name,
                    "message": f"Container '{c_name}' runs in privileged mode, granting full host node root access.",
                })

            # Privilege escalation
            if sc.get("allowPrivilegeEscalation") is True:
                findings.append({
                    "rule_id": "K8S_PRIVILEGE_ESCALATION",
                    "severity": "HIGH",
                    "container": c_name,
                    "message": f"Container '{c_name}' has allowPrivilegeEscalation=true.",
                })

        return findings

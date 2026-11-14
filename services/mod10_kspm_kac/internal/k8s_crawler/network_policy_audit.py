"""Kubernetes Network Policy & Namespace Segmentation Auditor (PRD-MOD-10).

Audits namespaces to ensure default-deny ingress/egress network policies are active,
preventing unrestricted pod-to-pod lateral movement.
"""

from typing import Any, Dict, List


class NetworkPolicyAuditor:
    """Audits namespace network policies to enforce microsegmentation."""

    @classmethod
    def audit_namespace_network_policies(
        cls,
        namespace: str,
        network_policies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        # System namespaces often managed by cloud providers (kube-system, kube-public, kube-node-lease)
        if namespace in ("kube-system", "kube-public", "kube-node-lease"):
            return []

        has_default_deny_ingress = False
        has_default_deny_egress = False

        for netpol in network_policies:
            spec = netpol.get("spec", {})
            pod_selector = spec.get("podSelector", {})
            match_labels = pod_selector.get("matchLabels", {})
            policy_types = spec.get("policyTypes", [])

            # An empty podSelector {} matches all pods in the namespace
            if not match_labels and pod_selector == {}:
                if "Ingress" in policy_types and "ingress" not in spec:
                    has_default_deny_ingress = True
                if "Egress" in policy_types and "egress" not in spec:
                    has_default_deny_egress = True

        if not has_default_deny_ingress:
            findings.append({
                "finding_code": "K8S_MISSING_DEFAULT_DENY_INGRESS",
                "severity": "MEDIUM",
                "namespace": namespace,
                "description": f"Namespace '{namespace}' lacks a default-deny Ingress NetworkPolicy, exposing pods to unrestricted lateral ingress.",
            })

        if not has_default_deny_egress:
            findings.append({
                "finding_code": "K8S_MISSING_DEFAULT_DENY_EGRESS",
                "severity": "LOW",
                "namespace": namespace,
                "description": f"Namespace '{namespace}' lacks a default-deny Egress NetworkPolicy, allowing unrestricted outbound egress.",
            })

        return findings

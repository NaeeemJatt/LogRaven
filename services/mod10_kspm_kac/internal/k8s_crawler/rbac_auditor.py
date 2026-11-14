"""Kubernetes RBAC Privilege Escalation & Wildcard Auditor (PRD-MOD-10 / TC-MOD10-003).

Audits ClusterRoles, Roles, and RoleBindings for dangerous permissions (* on secrets, full admin, impersonation).
"""

from typing import Any, Dict, List, Set


class RBACAuditor:
    """Analyzes Kubernetes RBAC policies for excessive privileges and security risks."""

    @classmethod
    def audit_cluster_role(
        cls,
        role_name: str,
        rules: List[Dict[str, Any]],
        is_cluster_scoped: bool = True,
    ) -> List[Dict[str, Any]]:
        """Audits RBAC policy rules of a ClusterRole or Role."""
        findings: List[Dict[str, Any]] = []

        for rule in rules:
            verbs = set(str(v).lower() for v in rule.get("verbs", []))
            resources = set(str(r).lower() for r in rule.get("resources", []))
            api_groups = set(str(g).lower() for g in rule.get("apiGroups", [""]))

            has_wildcard_verb = "*" in verbs
            has_wildcard_resource = "*" in resources

            # 1. Check for wildcard on secrets: verbs: ["*"] on resources: ["secrets"] (TC-MOD10-003)
            if ("secrets" in resources or has_wildcard_resource) and (has_wildcard_verb or "get" in verbs or "list" in verbs):
                if has_wildcard_verb:
                    findings.append({
                        "finding_code": "K8S_OVERLY_PERMISSIVE_SECRETS_ROLE",
                        "severity": "HIGH",
                        "role_name": role_name,
                        "resource": "secrets",
                        "verbs": list(verbs),
                        "description": f"Role '{role_name}' grants wildcard verb access ('*') to Kubernetes secrets, allowing complete cluster credential theft.",
                    })

            # 2. Complete cluster wildcard (* on *)
            if has_wildcard_verb and has_wildcard_resource:
                findings.append({
                    "finding_code": "K8S_CLUSTER_ROLE_FULL_ADMIN_WILDCARD",
                    "severity": "CRITICAL",
                    "role_name": role_name,
                    "description": f"Role '{role_name}' grants blanket wildcard access ('*' on '*').",
                })

            # 3. Privilege escalation verbs
            escalation_verbs = {"bind", "escalate", "impersonate"}.intersection(verbs)
            if escalation_verbs:
                findings.append({
                    "finding_code": "K8S_RBAC_ESCALATION_VERB",
                    "severity": "HIGH",
                    "role_name": role_name,
                    "verbs": list(escalation_verbs),
                    "description": f"Role '{role_name}' contains privilege escalation verbs: {list(escalation_verbs)}.",
                })

            # 4. Pod exec / attach privileges
            if "pods/exec" in resources and (has_wildcard_verb or "create" in verbs):
                findings.append({
                    "finding_code": "K8S_POD_EXEC_PERMISSION",
                    "severity": "MEDIUM",
                    "role_name": role_name,
                    "description": f"Role '{role_name}' allows remote shell execution into running pods (pods/exec).",
                })

        return findings

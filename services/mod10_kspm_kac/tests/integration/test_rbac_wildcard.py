"""Integration tests for Kubernetes RBAC Privilege Escalation & Wildcard Auditor (TC-MOD10-003).

Audits ClusterRoles granting wildcard access to secrets.
"""

import pytest

from services.mod10_kspm_kac.internal.k8s_crawler.rbac_auditor import RBACAuditor


def test_tc_mod10_003_rbac_wildcard_secrets_role_detected():
    """TC-MOD10-003: Crawl cluster with a ClusterRole granting verbs: ["*"] on resources: ["secrets"].

    Expected: Auditor generates finding K8S_OVERLY_PERMISSIVE_SECRETS_ROLE with High severity.
    """
    role_name = "secret-vault-sync-operator"
    rules = [
        {
            "apiGroups": [""],
            "resources": ["secrets"],
            "verbs": ["*"],
        },
        {
            "apiGroups": [""],
            "resources": ["configmaps"],
            "verbs": ["get", "list"],
        },
    ]

    findings = RBACAuditor.audit_cluster_role(
        role_name=role_name,
        rules=rules,
        is_cluster_scoped=True,
    )

    assert len(findings) > 0
    secrets_finding = next((f for f in findings if f["finding_code"] == "K8S_OVERLY_PERMISSIVE_SECRETS_ROLE"), None)
    assert secrets_finding is not None
    assert secrets_finding["severity"] == "HIGH"
    assert secrets_finding["resource"] == "secrets"
    assert "*" in secrets_finding["verbs"]


def test_rbac_least_privilege_role_passes():
    """Verifies targeted read-only role on pods passes without high-severity wildcard findings."""
    role_name = "pod-reader"
    rules = [
        {
            "apiGroups": [""],
            "resources": ["pods", "pods/log"],
            "verbs": ["get", "list", "watch"],
        }
    ]

    findings = RBACAuditor.audit_cluster_role(
        role_name=role_name,
        rules=rules,
        is_cluster_scoped=False,
    )

    assert len(findings) == 0

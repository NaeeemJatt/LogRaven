"""Unit tests for Pod Security Standards Privileged Container Admission (TC-MOD10-001).

Verifies that privileged container specs are blocked in ENFORCE mode and admitted with warnings in AUDIT mode.
"""

import pytest

from services.mod10_kspm_kac.internal.pss_evaluator.privileged_checker import PrivilegedChecker
from services.mod10_kspm_kac.internal.webhook_handler.response_builder import AdmissionResponseBuilder


def create_admission_review_privileged_pod():
    """Builds sample AdmissionReview fixture with a privileged container."""
    return {
        "uid": "705ab4f5-6393-11e8-b7cc-42010a800002",
        "spec": {
            "containers": [
                {
                    "name": "security-agent",
                    "image": "nginx:alpine",
                    "securityContext": {
                        "privileged": True,
                        "allowPrivilegeEscalation": True,
                    },
                }
            ]
        },
    }


def test_tc_mod10_001_privileged_pod_enforce_mode_rejected():
    """TC-MOD10-001 (Part A): Webhook responds with allowed: false in enforce mode."""
    fixture = create_admission_review_privileged_pod()
    findings = PrivilegedChecker.evaluate_pod_spec(fixture["spec"])

    # Build response in ENFORCE mode
    resp = AdmissionResponseBuilder.build_response(
        uid=fixture["uid"],
        findings=findings,
        enforcement_mode="ENFORCE",
    )

    review_resp = resp["response"]
    assert review_resp["uid"] == fixture["uid"]
    assert review_resp["allowed"] is False
    assert review_resp["status"]["code"] == 403
    assert "privileged mode" in review_resp["status"]["message"]


def test_tc_mod10_001_privileged_pod_audit_mode_admitted_with_warning():
    """TC-MOD10-001 (Part B): Webhook responds with allowed: true with audit warning in audit mode."""
    fixture = create_admission_review_privileged_pod()
    findings = PrivilegedChecker.evaluate_pod_spec(fixture["spec"])

    # Build response in AUDIT mode
    resp = AdmissionResponseBuilder.build_response(
        uid=fixture["uid"],
        findings=findings,
        enforcement_mode="AUDIT",
    )

    review_resp = resp["response"]
    assert review_resp["uid"] == fixture["uid"]
    assert review_resp["allowed"] is True
    assert review_resp["status"]["code"] == 200
    assert len(review_resp.get("warnings", [])) > 0
    assert any("AUDIT WARNING:" in w and "privileged mode" in w for w in review_resp["warnings"])


def test_compliant_pod_admitted():
    """Verifies unprivileged standard pod is admitted cleanly with zero warnings."""
    clean_pod = {
        "uid": "11223344-5566-7788-9900-aabbccddeeff",
        "spec": {
            "containers": [
                {
                    "name": "web-frontend",
                    "image": "nginx:alpine",
                    "securityContext": {
                        "privileged": False,
                        "allowPrivilegeEscalation": False,
                    },
                }
            ]
        },
    }
    findings = PrivilegedChecker.evaluate_pod_spec(clean_pod["spec"])
    resp = AdmissionResponseBuilder.build_response(
        uid=clean_pod["uid"],
        findings=findings,
        enforcement_mode="ENFORCE",
    )

    review_resp = resp["response"]
    assert review_resp["allowed"] is True
    assert review_resp["status"]["code"] == 200
    assert "warnings" not in review_resp or len(review_resp["warnings"]) == 0

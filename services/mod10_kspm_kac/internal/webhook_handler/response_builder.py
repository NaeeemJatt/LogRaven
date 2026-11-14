"""Kubernetes AdmissionReview v1 Response Builder (PRD-MOD-10 / TC-MOD10-001, TC-MOD10-002).

Constructs compliant admission.k8s.io/v1 responses honoring ENFORCE vs AUDIT modes.
"""

from typing import Any, Dict, List, Optional


class AdmissionResponseBuilder:
    """Builds standard Kubernetes AdmissionReview v1 responses."""

    @classmethod
    def build_response(
        cls,
        uid: str,
        findings: List[Dict[str, Any]],
        enforcement_mode: str = "ENFORCE",
    ) -> Dict[str, Any]:
        """Constructs AdmissionReview response.

        In ENFORCE mode:
          - If critical/high findings exist -> allowed: False with 403 status message.
        In AUDIT mode:
          - Always allowed: True, with policy violations returned in Kubernetes admission warnings.
        """
        mode = enforcement_mode.upper().strip()

        # Check for blocking violations
        has_blocking_violations = len(findings) > 0

        # Construct primary rejection message
        denial_message = ""
        if findings:
            # Check if any finding has an explicit DENIED prefix (e.g. socket mount)
            socket_finding = next((f for f in findings if f.get("rule_id") == "K8S_CONTAINER_RUNTIME_SOCKET_MOUNT"), None)
            if socket_finding:
                denial_message = socket_finding.get("message", "Mounting container runtime socket is prohibited.")
            else:
                top_finding = findings[0]
                msg = top_finding.get("message", "Violation of LogRaven KSPM policy")
                denial_message = f"DENIED by LogRaven KSPM: {msg}"

        if mode == "ENFORCE" and has_blocking_violations:
            allowed = False
            status_obj = {
                "code": 403,
                "message": denial_message,
            }
            warnings = [f.get("message") for f in findings if f.get("message")]
        else:
            allowed = True
            status_obj = {
                "code": 200,
                "message": "Admitted by LogRaven KSPM",
            }
            # In audit mode, emit warnings so developer/kubectl sees the policy audit alert
            warnings = [f"AUDIT WARNING: {f.get('message')}" for f in findings if f.get("message")]

        response_body: Dict[str, Any] = {
            "uid": uid,
            "allowed": allowed,
            "status": status_obj,
        }
        if warnings:
            response_body["warnings"] = warnings

        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": response_body,
        }

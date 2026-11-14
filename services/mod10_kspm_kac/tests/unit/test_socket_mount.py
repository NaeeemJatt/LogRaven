"""Unit tests for Container Runtime Socket Mount Rejection (TC-MOD10-002).

Verifies rejection of pods attempting to mount /var/run/docker.sock with the exact expected denial message.
"""

import pytest

from services.mod10_kspm_kac.internal.pss_evaluator.socket_mount_checker import SocketMountChecker
from services.mod10_kspm_kac.internal.webhook_handler.response_builder import AdmissionResponseBuilder


def test_tc_mod10_002_docker_socket_mount_rejected():
    """TC-MOD10-002: Send Pod spec mounting /var/run/docker.sock.

    Expected: Rejects request with message 'DENIED: Mounting container runtime socket is prohibited by LogRaven KSPM policy'.
    """
    pod_spec = {
        "containers": [
            {
                "name": "dind-sidecar",
                "image": "docker:dind",
                "volumeMounts": [
                    {
                        "name": "dockersock",
                        "mountPath": "/var/run/docker.sock",
                    }
                ],
            }
        ],
        "volumes": [
            {
                "name": "dockersock",
                "hostPath": {
                    "path": "/var/run/docker.sock",
                },
            }
        ],
    }

    # 1. Run socket mount auditor
    findings = SocketMountChecker.evaluate_pod_spec(pod_spec)
    assert len(findings) > 0

    # 2. Build admission response
    uid = "a1b2c3d4-e5f6-7890-abcd-ef0123456789"
    resp = AdmissionResponseBuilder.build_response(
        uid=uid,
        findings=findings,
        enforcement_mode="ENFORCE",
    )

    review_resp = resp["response"]
    assert review_resp["allowed"] is False
    assert review_resp["status"]["code"] == 403
    # Check exact expected denial message
    expected_message = "DENIED: Mounting container runtime socket is prohibited by LogRaven KSPM policy"
    assert review_resp["status"]["message"] == expected_message


def test_safe_volume_mount_allowed():
    """Verifies standard emptyDir / configMap volumes pass without socket flags."""
    safe_pod = {
        "containers": [
            {
                "name": "app",
                "image": "python:3.14-slim",
                "volumeMounts": [
                    {
                        "name": "cache-volume",
                        "mountPath": "/tmp/cache",
                    }
                ],
            }
        ],
        "volumes": [
            {
                "name": "cache-volume",
                "emptyDir": {},
            }
        ],
    }
    findings = SocketMountChecker.evaluate_pod_spec(safe_pod)
    assert len(findings) == 0

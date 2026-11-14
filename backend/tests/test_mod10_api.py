"""API integration tests for Module 10: KSPM & Kubernetes Admission Controller Webhook."""

import sys
if "ujson" not in sys.modules:
    sys.modules["ujson"] = None

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="kspm-sec@lograven.io",
        name="K8s Security Engineer",
        password_hash="argon2id$mocked$hash",
        email_verified=True,
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None),
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
        )
    )
    return db


@pytest.mark.asyncio
async def test_kspm_validate_webhook_privileged_enforce_and_audit():
    """Tests /api/v1/kspm/validate handles AdmissionReview for privileged container."""
    review_req = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": "test-uid-12345",
            "kind": {"group": "", "version": "v1", "kind": "Pod"},
            "resource": {"group": "", "version": "v1", "resource": "pods"},
            "namespace": "production",
            "operation": "CREATE",
            "object": {
                "metadata": {"name": "privileged-test-pod"},
                "spec": {
                    "containers": [
                        {
                            "name": "attacker",
                            "image": "ubuntu:latest",
                            "securityContext": {"privileged": True},
                        }
                    ]
                },
            },
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 1. Test ENFORCE mode -> rejected
        resp_enforce = await client.post("/api/v1/kspm/validate?mode=ENFORCE", json=review_req)
        assert resp_enforce.status_code == 200
        data_enforce = resp_enforce.json()
        assert data_enforce["response"]["allowed"] is False
        assert data_enforce["response"]["status"]["code"] == 403

        # 2. Test AUDIT mode -> admitted with warning
        resp_audit = await client.post("/api/v1/kspm/validate?mode=AUDIT", json=review_req)
        assert resp_audit.status_code == 200
        data_audit = resp_audit.json()
        assert data_audit["response"]["allowed"] is True
        assert data_audit["response"]["status"]["code"] == 200
        assert len(data_audit["response"]["warnings"]) > 0


@pytest.mark.asyncio
async def test_kspm_validate_webhook_socket_mount():
    """Tests /api/v1/kspm/validate rejects docker socket mount with exact denial message."""
    review_req = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": "socket-uid-9999",
            "kind": {"group": "", "version": "v1", "kind": "Pod"},
            "namespace": "default",
            "operation": "CREATE",
            "object": {
                "metadata": {"name": "socket-mount-pod"},
                "spec": {
                    "containers": [
                        {
                            "name": "dind",
                            "image": "docker:dind",
                            "volumeMounts": [{"name": "sock", "mountPath": "/var/run/docker.sock"}],
                        }
                    ],
                    "volumes": [{"name": "sock", "hostPath": {"path": "/var/run/docker.sock"}}],
                },
            },
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/kspm/validate?mode=ENFORCE", json=review_req)

    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]["allowed"] is False
    assert (
        data["response"]["status"]["message"]
        == "DENIED: Mounting container runtime socket is prohibited by LogRaven KSPM policy"
    )


@pytest.mark.asyncio
async def test_kspm_audit_rbac_endpoint(test_user):
    """Tests /api/v1/kspm/audit/rbac detects overly permissive secrets role."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    req_body = {
        "role_name": "secrets-wildcard-role",
        "rules": [
            {
                "apiGroups": [""],
                "resources": ["secrets"],
                "verbs": ["*"],
            }
        ],
        "is_cluster_scoped": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/kspm/audit/rbac", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_compliant"] is False
    codes = [f["finding_code"] for f in data["findings"]]
    assert "K8S_OVERLY_PERMISSIVE_SECRETS_ROLE" in codes


@pytest.mark.asyncio
async def test_kspm_register_and_list_clusters(test_user, mock_db):
    """Tests /api/v1/kspm/clusters registration endpoint."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    req_body = {
        "asset_urn": "urn:lograven:k8s:aws:123456789012:us-east-1:eks:cluster/production-core",
        "cluster_name": "production-core",
        "distribution": "EKS",
        "k8s_version": "v1.30.2",
        "kac_webhook_installed": True,
        "kac_enforcement_mode": "ENFORCE",
        "namespaces_count": 12,
        "pods_count": 84,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/kspm/clusters", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["cluster_name"] == "production-core"
    assert data["kac_enforcement_mode"] == "ENFORCE"

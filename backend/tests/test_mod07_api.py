"""API integration tests for Module 07: CIEM & ChatOps JIT Broker."""

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
        email="identity-sec@lograven.io",
        name="CIEM Security Engineer",
        password_hash="argon2id$mocked$hash",
        email_verified=True,
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None), scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    return db


@pytest.mark.asyncio
async def test_evaluate_permissions_api(test_user, mock_db):
    """Verifies /api/v1/ciem/evaluate-permissions computes 5-layer math and detects toxic combinations."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "principal_arn": "arn:aws:iam::123456789012:role/DevSecOpsRole",
        "provider": "aws",
        "identity_policies": [
            {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["iam:PassRole", "ec2:RunInstances", "s3:*"],
                        "Resource": "*",
                    }
                ]
            }
        ],
        "scp_policies": [
            {
                "Statement": [
                    {
                        "Effect": "Deny",
                        "Action": "s3:*",
                        "Resource": "*",
                    }
                ]
            }
        ],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/ciem/evaluate-permissions", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["principal_arn"] == payload["principal_arn"]
        assert data["scp_override_applied"] is True
        # Verify s3:* was denied and not in effective actions
        assert not any(a.lower().startswith("s3:") for a in data["effective_actions"])
        # Verify toxic privilege escalation vector detected (iam:PassRole + ec2:RunInstances)
        assert data["has_toxic_combinations"] is True
        vector_ids = [v["vector_id"] for v in data["toxic_vectors"]]
        assert "AWS-PRIVESC-002" in vector_ids

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_right_size_entitlement_api(test_user):
    """Verifies /api/v1/ciem/right-size calculates usage diff and generates least-privilege policy."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    payload = {
        "principal_arn": "arn:aws:iam::123456789012:role/OverprivilegedAppRole",
        "granted_actions": [f"ec2:Action{i}" for i in range(50)],
        "used_actions_90d": ["ec2:DescribeInstances", "ec2:StopInstances"],
        "resource_arn": "arn:aws:ec2:us-east-1:123456789012:instance/*",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/ciem/right-size", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["usage_diff"]["total_granted_count"] == 50
        assert data["usage_diff"]["used_actions_count"] == 2
        assert data["usage_diff"]["is_overprivileged"] is True
        rec_policy = data["recommended_policy"]["policy_document"]
        assert rec_policy["Statement"][0]["Action"] == sorted(payload["used_actions_90d"])

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_jit_lease_lifecycle_api(test_user, mock_db):
    """Verifies JIT request, approval, and listing endpoints."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 1. Request JIT lease
        req_body = {
            "target_role_arn": "arn:aws:iam::123456789012:role/EmergencyProdRole",
            "duration_minutes": 45,
            "justification": "Production DB migration debug",
        }
        res_req = await client.post("/api/v1/ciem/jit/request", json=req_body)
        assert res_req.status_code == 200
        req_data = res_req.json()
        assert req_data["status"] == "REQUESTED"
        lease_id = req_data["lease"]["lease_id"]

        # 2. Approve JIT lease
        res_app = await client.post("/api/v1/ciem/jit/approve", json={"lease_id": lease_id})
        assert res_app.status_code == 200
        app_data = res_app.json()
        assert app_data["status"] == "ACTIVE"
        assert app_data["lease"]["session_token_id"] is not None

        # 3. List leases
        res_list = await client.get("/api/v1/ciem/jit/leases")
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert len(list_data) >= 1

        # 4. Revoke lease
        res_rev = await client.post("/api/v1/ciem/jit/revoke", json={"lease_id": lease_id})
        assert res_rev.status_code == 200
        assert res_rev.json()["status"] == "REVOKED"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_toxic_vectors_api(test_user):
    """Verifies /api/v1/ciem/toxic-vectors returns full 21-vector catalog."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.get("/api/v1/ciem/toxic-vectors")
        assert res.status_code == 200
        vectors = res.json()
        assert len(vectors) >= 21
        vector_ids = [v["id"] for v in vectors]
        assert "AWS-PRIVESC-002" in vector_ids

    app.dependency_overrides.clear()

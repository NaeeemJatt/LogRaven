"""API integration tests for Module 12: Visual-to-Rego Studio, Suppressions, & Audit Vault."""

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
        email="audit-officer@lograven.io",
        name="Chief Compliance Officer",
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
            rowcount=0,
        )
    )
    return db


@pytest.mark.asyncio
async def test_policy_compile_endpoint(test_user):
    """Tests /api/v1/policies/compile endpoint translates visual condition tree into valid Rego."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    req_body = {
        "rule_id": "CUSTOM-S3-VERSIONING",
        "resource_type": "aws_s3_bucket",
        "conditions": [
            {"field": "versioning.status", "operator": "!=", "value": "Enabled"}
        ],
        "message": "S3 bucket versioning is not enabled",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/policies/compile", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert "package lograven.rules.custom" in data["rego_code"]
    assert 'input.versioning.status != "Enabled"' in data["rego_code"]


@pytest.mark.asyncio
async def test_suppression_evaluate_endpoint(test_user, mock_db):
    """Tests /api/v1/policies/suppressions/evaluate endpoint."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    req_body = {
        "finding_type": "IOM-S3-PUBLIC-ACL",
        "account_id": "123456789012",
        "region": "us-east-1",
        "tags": {"Environment": "Production"},
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/policies/suppressions/evaluate", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert "is_suppressed" in data


@pytest.mark.asyncio
async def test_suppression_sweep_endpoint(test_user, mock_db):
    """Tests /api/v1/policies/suppressions/sweep endpoint."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/policies/suppressions/sweep")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "expired_count" in data


@pytest.mark.asyncio
async def test_vault_package_and_verify_endpoints(test_user, mock_db):
    """Tests /api/v1/policies/vault/package creates vault zip and /vault/verify validates it."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    req_body = {
        "package_name": "soc2_evidence",
        "files": {
            "evidence.json": '{"audit": "passed", "soc2_type2": true}',
            "manifest_note.txt": "Cryptographic vault verification test note",
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        pkg_resp = await client.post("/api/v1/policies/vault/package", json=req_body)
        assert pkg_resp.status_code == 200
        pkg_data = pkg_resp.json()
        assert "merkle_root_hash" in pkg_data
        assert "package_base64" in pkg_data

        verify_resp = await client.post(
            "/api/v1/policies/vault/verify",
            json={"package_base64": pkg_data["package_base64"]},
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["is_valid"] is True
        assert verify_data["status"] == "VERIFIED"


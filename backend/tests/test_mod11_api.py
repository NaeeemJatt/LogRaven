"""API integration tests for Module 11: ASPM, IaC AST Scanner, & GitOps Auto-PR."""

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
        email="aspm-devops@lograven.io",
        name="Platform Security Engineer",
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
async def test_iac_patch_endpoint(test_user):
    """Tests /api/v1/iac/patch surgically modifies HCL attribute while preserving comments."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    hcl = (
        '# S3 Bucket Configuration\n'
        'resource "aws_s3_bucket_public_access_block" "b" {\n'
        '  block_public_acls = false\n'
        '}\n'
    )
    req_body = {
        "hcl_content": hcl,
        "attribute": "block_public_acls",
        "new_value": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/iac/patch", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["modified"] is True
    assert "  block_public_acls = true\n" in data["patched_content"]
    assert "# S3 Bucket Configuration" in data["patched_content"]


@pytest.mark.asyncio
async def test_iac_lineage_correlate_endpoint(test_user, mock_db):
    """Tests /api/v1/iac/lineage/correlate maps cloud asset tags back to source repo and line."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    req_body = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:s3:bucket/acme-prod-data",
        "tags": {
            "git_repo": "acme/infra",
            "git_file": "main.tf",
            "git_line": "42",
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/iac/lineage/correlate", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_lineage"] is True
    assert data["repo_full_name"] == "acme/infra"
    assert data["file_path"] == "main.tf"
    assert data["line_number"] == 42


@pytest.mark.asyncio
async def test_iac_remediate_pr_endpoint(test_user, mock_db):
    """Tests /api/v1/iac/remediate/pr creates automated GitHub Pull Request."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    req_body = {
        "repo_full_name": "acme/infra",
        "base_branch": "main",
        "rule_id": "IOM-S3-PUBLIC-ACL",
        "file_path": "terraform/s3.tf",
        "diff_text": "- block_public_acls = false\n+ block_public_acls = true",
        "pr_number": 104,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/iac/remediate/pr", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["pr_number"] == 104
    assert data["pr_url"] == "https://github.com/acme/infra/pull/104"
    assert data["status"] == "OPEN"


@pytest.mark.asyncio
async def test_cloudbot_emergency_action(test_user):
    """Tests /api/v1/iac/cloudbots/action executes emergency serverless remediation."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    req_body = {
        "bot_id": "bot-s3-block-public",
        "target_resource": "unprotected-data-lake",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/iac/cloudbots/action", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["bot_id"] == "bot-s3-block-public"
    assert data["parameters"]["BlockPublicAcls"] is True

"""Functional tests for Module 02 REST endpoints and CAASM core engine."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.dependencies import get_current_user, get_db
from services.mod02_asset_crawler.internal.repository.models import CSPMAsset
from services.mod02_asset_crawler.internal.normalizer.urn_builder import build_urn
from services.mod02_asset_crawler.internal.normalizer.canonical_hasher import compute_canonical_sha256


@pytest.fixture
def mock_user():
    return User(
        id=uuid.uuid4(),
        email="asset-auditor@lograven.local",
        password_hash="test-password-hash",
        tier="team",
        email_verified=True,
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_list_assets_endpoint(mock_user, mock_db):
    """Test GET /api/v1/assets lists normalized asset entities."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    urn = build_urn("aws", "123456789012", "us-east-1", "s3", "aws_s3_bucket", "my-sec-vault")
    sample_asset = CSPMAsset(
        urn=urn,
        tenant_id=mock_user.id,
        account_id="123456789012",
        provider="aws",
        region="us-east-1",
        service="s3",
        resource_type="aws_s3_bucket",
        resource_id="my-sec-vault",
        resource_name="my-sec-vault",
        config_json={"encryption": True},
        config_sha256=compute_canonical_sha256({"encryption": True}),
        is_deleted=False,
    )

    with patch("services.mod02_asset_crawler.cmd.crawler.main.AssetRepository.list_assets", return_value=[sample_asset]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/assets")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            assert data[0]["urn"] == urn
            assert data[0]["provider"] == "aws"
            assert data[0]["resource_type"] == "aws_s3_bucket"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_asset_by_urn_endpoint(mock_user, mock_db):
    """Test GET /api/v1/assets/{urn} retrieves specific asset by URN."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    urn = build_urn("aws", "123456789012", "us-east-1", "ec2", "aws_instance", "i-0998877")
    sample_asset = CSPMAsset(
        urn=urn,
        tenant_id=mock_user.id,
        account_id="123456789012",
        provider="aws",
        region="us-east-1",
        service="ec2",
        resource_type="aws_instance",
        resource_id="i-0998877",
        resource_name="i-0998877",
        config_json={"state": "running"},
        config_sha256=compute_canonical_sha256({"state": "running"}),
        is_deleted=False,
    )

    with patch("services.mod02_asset_crawler.cmd.crawler.main.AssetRepository.get_by_urn", return_value=sample_asset):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(f"/api/v1/assets/{urn}")
            assert res.status_code == 200
            data = res.json()
            assert data["urn"] == urn
            assert data["resource_id"] == "i-0998877"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trigger_account_crawl_endpoint(mock_user, mock_db):
    """Test POST /api/v1/assets/crawl executes crawler and returns delta metrics."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_summary = {
        "account_id": "123456789012",
        "provider": "aws",
        "total_discovered": 42,
        "mutated_assets": 5,
        "tombstoned_assets": 1,
        "active_assets": 41,
    }

    with patch("services.mod02_asset_crawler.cmd.crawler.main._collector.crawl_account", return_value=[]):
        with patch("services.mod02_asset_crawler.cmd.crawler.main.process_account_crawl", return_value=mock_summary):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/assets/crawl",
                    json={
                        "account_id": "123456789012",
                        "provider": "aws",
                        "regions": ["us-east-1"],
                    },
                )
                assert res.status_code == 200
                data = res.json()
                assert data["account_id"] == "123456789012"
                assert data["total_discovered"] == 42
                assert data["mutated_assets"] == 5
                assert data["tombstoned_assets"] == 1

    app.dependency_overrides.clear()


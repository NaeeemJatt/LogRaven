"""API integration tests for Module 08: DSPM Data Sampling & Classification Engine."""

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
        email="dspm-sec@lograven.io",
        name="Data Security Officer",
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
async def test_dspm_scan_endpoint_reservoir_and_pci_pii(test_user, mock_db):
    """Verifies /api/v1/dspm/scan samples files and classifies PII/PCI with D_sens score."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    sample_files = {
        "customers.csv": "Name,SSN,Card\nAlice,123-45-6789,4532015000000007\n",
        "readme.txt": "Public documentation without secrets",
    }

    payload = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:s3:bucket/prod-customer-lake",
        "storage_type": "s3",
        "total_objects_count": 500,
        "encryption_type": "CMK_KMS",
        "is_versioning_enabled": True,
        "is_object_lock_enabled": False,
        "sample_files": sample_files,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/dspm/scan", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["sampled_objects_count"] == 2
        assert data["sensitivity"]["contains_pii"] is True
        assert data["sensitivity"]["contains_pci"] is True
        assert data["sensitivity"]["d_sens_score"] == 100.0
        assert data["posture"]["is_ransomware_vulnerable"] is False
        assert data["posture"]["has_customer_managed_key"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dspm_classify_text_endpoint(test_user):
    """Verifies on-demand /api/v1/dspm/classify-text endpoint."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    payload = {
        "text_content": "Emergency API token: ghp_123456789012345678901234567890123456 and SSN: 987-65-4321",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/dspm/classify-text", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["findings_count"] >= 2
        detectors = [f["detector_name"] for f in data["findings"]]
        assert "GITHUB_PERSONAL_ACCESS_TOKEN" in detectors
        assert "US_SSN" in detectors

    app.dependency_overrides.clear()

"""Integration and functional API tests for Module 01 REST endpoints."""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.dependencies import get_current_user, get_db
from services.mod01_onboarding.internal.repository.models import CloudAccountV2, CloudGroup
from services.mod01_onboarding.internal.crypto import generate_external_id, encrypt_external_id


@pytest.fixture
def mock_user():
    return User(
        id=uuid.uuid4(),
        email="compliance-admin@lograven.local",
        password_hash="test-password-hash",
        tier="team",
        email_verified=True,
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Mock database session
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_register_cloud_account_endpoint(mock_user, mock_db):
    """Test POST /api/v1/cloud-connect/accounts generates ExternalId & templates."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("services.mod01_onboarding.cmd.server.main.AccountRepository.get_by_native_id", return_value=None):
        with patch("services.mod01_onboarding.cmd.server.main.AccountRepository.create_account") as mock_create:
            mock_account = CloudAccountV2(
                id=uuid.uuid4(),
                tenant_id=mock_user.id,
                provider="aws",
                native_account_id="123456789012",
                role_arn_or_sp="arn:aws:iam::123456789012:role/LogRavenCSPMReader",
                external_id_enc=encrypt_external_id("lr-ext-mock123"),
                status="PENDING_VALIDATION",
            )
            mock_create.return_value = (mock_account, "lr-ext-mock123")

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/cloud-connect/accounts",
                    json={
                        "provider": "aws",
                        "native_account_id": "123456789012",
                        "organization_id": "o-xyz12345",
                        "environment": "prod",
                    },
                )

                assert res.status_code == 201
                data = res.json()
                assert data["account_id"] == str(mock_account.id)
                assert data["external_id"] == "lr-ext-mock123"
                assert "lr-ingest-" in data["event_bus_arn"]
                assert "cloudformation_url" in data["templates"]
                assert "terraform_hcl" in data["templates"]
                assert "LogRavenCSPMReader" in data["templates"]["terraform_hcl"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_validate_cloud_account_endpoint(mock_user, mock_db):
    """Test POST /api/v1/cloud-connect/accounts/{id}/validate checks STS and policy simulation."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    account_id = uuid.uuid4()
    mock_account = CloudAccountV2(
        id=account_id,
        tenant_id=mock_user.id,
        provider="aws",
        native_account_id="123456789012",
        role_arn_or_sp="arn:aws:iam::123456789012:role/LogRavenCSPMReader",
        external_id_enc=encrypt_external_id("lr-ext-mock123"),
        status="PENDING_VALIDATION",
    )

    with patch("services.mod01_onboarding.cmd.server.main.AccountRepository.get_by_id", return_value=mock_account):
        with patch("services.mod01_onboarding.cmd.server.main._sts_broker.get_credentials", return_value=({"access_key_id": "MOCK"}, False)):
            with patch("services.mod01_onboarding.cmd.server.main._policy_simulator.verify_permissions") as mock_sim:
                mock_sim.return_value = {
                    "status": "CONNECTED",
                    "iom_ready": True,
                    "ioa_stream_ready": True,
                    "missing_permissions": [],
                }
                with patch("services.mod01_onboarding.cmd.server.main.AccountRepository.update_status", return_value=mock_account):
                    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                        res = await client.post(f"/api/v1/cloud-connect/accounts/{account_id}/validate")
                        assert res.status_code == 200
                        data = res.json()
                        assert data["status"] == "CONNECTED"
                        assert data["iom_ready"] is True
                        assert data["ioa_stream_ready"] is True
                        assert data["missing_permissions"] == []

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cloud_groups_endpoints(mock_user, mock_db):
    """Test POST & GET /api/v1/cloud-connect/groups."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    group_id = uuid.uuid4()
    mock_group = CloudGroup(
        id=group_id,
        tenant_id=mock_user.id,
        name="Production PCI Fleet",
        business_impact="critical",
        environment="prod",
        account_ids=[],
        tag_filters={"Tier": "PaymentGateway"},
    )

    with patch("services.mod01_onboarding.cmd.server.main.GroupRepository.create_group", return_value=mock_group):
        with patch("services.mod01_onboarding.cmd.server.main.GroupRepository.list_groups", return_value=[mock_group]):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Create group
                res = await client.post(
                    "/api/v1/cloud-connect/groups",
                    json={
                        "name": "Production PCI Fleet",
                        "business_impact": "critical",
                        "environment": "prod",
                        "tag_filters": {"Tier": "PaymentGateway"},
                    },
                )
                assert res.status_code == 201

                # List groups
                res = await client.get("/api/v1/cloud-connect/groups")
                assert res.status_code == 200
                data = res.json()
                assert len(data) == 1
                assert data[0]["name"] == "Production PCI Fleet"

    app.dependency_overrides.clear()

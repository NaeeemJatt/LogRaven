"""Tests for Multi-Cloud Fleet Expansion (GCP & Azure)."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.compliance.collectors import get_collector, GCPCollector, AzureCollector, AWSCollector
from app.compliance.frameworks import get_framework, is_registered, list_frameworks
from app.compliance.graph.builder import build_attack_path_graph
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.soc2_audit import CloudAccount


class _FakeDb:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.refresh = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock()

    def add(self, row):
        self.added.append(row)

    async def delete(self, row):
        self.deleted.append(row)


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


@pytest.fixture
def fake_db():
    return _FakeDb()


@pytest.fixture
def client(fake_db):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="devsecops@enterprise.corp",
        tier="enterprise",
        password_hash="$2b$stub",
    )

    async def override_user():
        return user

    async def override_db():
        yield fake_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c, user, fake_db
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_cis_gcp_and_cis_azure_frameworks_registered():
    """Verify CIS GCP and CIS Azure benchmarks are registered in framework catalog."""
    assert is_registered("cis_gcp")
    assert is_registered("cis_azure")

    gcp_fw = get_framework("cis_gcp")
    assert gcp_fw is not None
    assert gcp_fw.name == "CIS Google Cloud Platform Benchmark"
    assert len(gcp_fw.controls) >= 10

    azure_fw = get_framework("cis_azure")
    assert azure_fw is not None
    assert azure_fw.name == "CIS Microsoft Azure Benchmark"
    assert len(azure_fw.controls) >= 10


def test_collector_factory_and_verification():
    """Verify factory returns appropriate collector and verifies credentials."""
    aws_coll = get_collector("aws")
    assert isinstance(aws_coll, AWSCollector)

    gcp_coll = get_collector("gcp")
    assert isinstance(gcp_coll, GCPCollector)

    azure_coll = get_collector("azure")
    assert isinstance(azure_coll, AzureCollector)

    # GCP verification
    valid_gcp = gcp_coll.verify_credentials({
        "gcp_project_id": "production-bigquery-lake",
        "gcp_service_account_email": "lograven-audit@production-bigquery-lake.iam.gserviceaccount.com",
    })
    assert valid_gcp["healthy"] is True
    assert valid_gcp["account_id"] == "production-bigquery-lake"

    # Azure verification
    valid_azure = azure_coll.verify_credentials({
        "azure_tenant_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
        "azure_subscription_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "azure_client_id": "client-id-12345",
    })
    assert valid_azure["healthy"] is True
    assert valid_azure["account_id"] == "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"


def test_gcp_collector_evidence_collection():
    """Verify GCPCollector outputs normalized telemetry compatible with signals engine."""
    collector = GCPCollector()
    evidence = collector.collect_evidence(
        {
            "gcp_project_id": "analytics-core-prod",
            "gcp_service_account_email": "audit@analytics-core-prod.iam.gserviceaccount.com",
        },
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
    )

    assert evidence["provider"] == "gcp"
    assert evidence["project_id"] == "analytics-core-prod"
    assert "storage" in evidence
    assert "iam" in evidence
    assert "logging" in evidence
    assert "network" in evidence
    assert "kms" in evidence
    assert evidence["storage"]["uniform_bucket_level_access_rate"] == 100.0


def test_azure_collector_evidence_collection():
    """Verify AzureCollector outputs normalized telemetry."""
    collector = AzureCollector()
    evidence = collector.collect_evidence(
        {
            "azure_subscription_id": "sub-1234-5678",
            "azure_tenant_id": "tenant-abcd",
            "azure_client_id": "client-xyz",
        },
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
    )

    assert evidence["provider"] == "azure"
    assert evidence["subscription_id"] == "sub-1234-5678"
    assert "storage" in evidence
    assert "iam" in evidence
    assert "logging" in evidence
    assert "network" in evidence
    assert evidence["storage"]["blob_public_access_disabled_rate"] == 100.0


def test_create_gcp_cloud_account_api(client):
    """Test POST /api/v1/compliance/accounts for Google Cloud Platform."""
    c, user, db = client

    response = c.post(
        "/api/v1/compliance/accounts",
        json={
            "name": "BigQuery Analytics Project",
            "provider": "gcp",
            "gcp_project_id": "gcp-analytics-prod-01",
            "gcp_service_account_email": "lograven@gcp-analytics-prod-01.iam.gserviceaccount.com",
            "default_frameworks": ["cis_gcp", "soc2"],
            "scan_schedule": "weekly",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "BigQuery Analytics Project"
    assert data["provider"] == "gcp"
    assert data["account_id"] == "gcp-analytics-prod-01"
    assert data["gcp_project_id"] == "gcp-analytics-prod-01"
    assert "cis_gcp" in data["default_frameworks"]


def test_create_azure_cloud_account_api(client):
    """Test POST /api/v1/compliance/accounts for Microsoft Azure."""
    c, user, db = client

    response = c.post(
        "/api/v1/compliance/accounts",
        json={
            "name": "Production Azure Tenant",
            "provider": "azure",
            "azure_tenant_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
            "azure_subscription_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
            "azure_client_id": "client-app-1234",
            "default_frameworks": ["cis_azure", "iso27001"],
            "scan_schedule": "daily",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Production Azure Tenant"
    assert data["provider"] == "azure"
    assert data["account_id"] == "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    assert data["azure_tenant_id"] == "72f988bf-86f1-41af-91ab-2d7cd011db47"
    assert "cis_azure" in data["default_frameworks"]


def test_verify_multi_cloud_account_api(client):
    """Test pre-flight verification on GCP and Azure cloud accounts."""
    c, user, db = client
    acc_id = uuid.uuid4()
    mock_gcp = SimpleNamespace(
        id=acc_id,
        user_id=user.id,
        name="GCP Core",
        provider="gcp",
        role_arn=None,
        account_id="gcp-core-1",
        gcp_project_id="gcp-core-1",
        gcp_service_account_email="sa@gcp-core-1.iam.gserviceaccount.com",
        gcp_workload_identity_pool=None,
        azure_tenant_id=None,
        azure_subscription_id=None,
        azure_client_id=None,
        default_frameworks=["cis_gcp"],
        scan_schedule="weekly",
        next_run_at=None,
        last_scanned_at=None,
        health_status="unverified",
        health_error=None,
        created_at=None,
    )
    db.execute.return_value = _ScalarResult(mock_gcp)

    response = c.post(f"/api/v1/compliance/accounts/{acc_id}/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["health_status"] == "connected"
    assert data["health_error"] is None


def test_build_attack_path_graph_multi_cloud_labels():
    """Verify build_attack_path_graph generates provider-specific asset labels."""
    gcp_graph = build_attack_path_graph(
        {"open_security_groups": 1, "s3_public_access_blocked": False},
        provider="gcp",
    )
    labels = [n.label for n in gcp_graph.nodes]
    assert any("VPC Firewall Rules" in l for l in labels)
    assert any("Cloud Storage Bucket" in l for l in labels)
    assert any("Compute Engine VM" in l for l in labels)
    assert all(n.provider == "gcp" for n in gcp_graph.nodes)

    azure_graph = build_attack_path_graph(
        {"open_security_groups": 1, "s3_public_access_blocked": False},
        provider="azure",
    )
    az_labels = [n.label for n in azure_graph.nodes]
    assert any("Network Security Group" in az_labels for az_labels in az_labels if "Network Security Group" in az_labels)
    assert any("Azure Blob Storage" in az_labels for az_labels in az_labels if "Azure Blob Storage" in az_labels)
    assert all(n.provider == "azure" for n in azure_graph.nodes)

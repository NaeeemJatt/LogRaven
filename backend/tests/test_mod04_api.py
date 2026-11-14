"""API integration tests for Module 04: Workload Disk Snapshot Scanner & CVE Engine."""

import sys
if "ujson" not in sys.modules:
    sys.modules["ujson"] = None

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import User
from services.mod04_disk_scanner.internal.repository.models import WorkloadSBOM, WorkloadVulnerability


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="workload-sec@lograven.io",
        name="Workload Security Engineer",
        password_hash="argon2id$mocked$hash",
        email_verified=True,
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_trigger_workload_scan_api(test_user, mock_db):
    """Verifies /api/v1/workloads/scan generates CycloneDX SBOM and returns scan metrics."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    target_urn = "urn:lograven:aws:123456789012:us-east-1:ec2:aws_instance/i-scan-01"
    scan_result = {
        "asset_urn": target_urn,
        "scan_status": "COMPLETED",
        "scan_duration_sec": 4,
        "packages_count": 2,
        "vulnerabilities_count": 1,
        "cisa_kev_count": 1,
        "secrets_count": 0,
        "sbom": {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "serialNumber": "urn:uuid:mocked-serial",
            "version": 1,
            "components": [],
        },
        "vulnerabilities": [
            {
                "cve_id": "CVE-2022-0778",
                "package_name": "openssl",
                "installed_version": "1.1.1k",
                "cvss_v3_score": 9.8,
                "is_cisa_kev": True,
                "epss_score": 0.9421,
            }
        ],
        "secrets": [],
    }

    payload = {
        "asset_urn": target_urn,
        "volume_id": "vol-1234567890abcdef0",
        "account_id": "123456789012",
        "region": "us-east-1",
        "os_family_hint": "ubuntu",
        "os_version_hint": "22.04",
    }

    with patch("services.mod04_disk_scanner.cmd.scanner_worker.main.execute_workload_scan", return_value=scan_result):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            res = await client.post("/api/v1/workloads/scan", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["asset_urn"] == payload["asset_urn"]
            assert data["scan_status"] == "COMPLETED"
            assert data["sbom"]["bomFormat"] == "CycloneDX"
            assert data["cisa_kev_count"] == 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_workload_sbom_api(test_user, mock_db):
    """Verifies /api/v1/workloads/sboms/{asset_urn} retrieves stored CycloneDX v1.5 JSON."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    target_urn = "urn:lograven:aws:123456789012:us-east-1:ec2:aws_instance/i-sbom-02"
    mock_record = WorkloadSBOM(
        asset_urn=target_urn,
        tenant_id=test_user.id,
        os_family="ubuntu",
        os_version="22.04",
        cyclonedx_sbom={"bomFormat": "CycloneDX", "specVersion": "1.5", "components": []},
        packages_count=0,
    )

    with patch("services.mod04_disk_scanner.cmd.scanner_worker.main.WorkloadRepository.get_sbom", return_value=mock_record):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            res = await client.get(f"/api/v1/workloads/sboms/{target_urn}")
            assert res.status_code == 200
            data = res.json()
            assert data["bomFormat"] == "CycloneDX"
            assert data["specVersion"] == "1.5"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_workload_vulnerabilities_api(test_user, mock_db):
    """Verifies /api/v1/workloads/vulnerabilities endpoint with CISA KEV filter."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_vuln = WorkloadVulnerability(
        id=uuid.uuid4(),
        asset_urn="urn:lograven:aws:123456789012:us-east-1:ec2:aws_instance/i-vuln-03",
        tenant_id=test_user.id,
        cve_id="CVE-2022-0778",
        package_name="openssl",
        installed_version="1.1.1k",
        cvss_v3_score=9.8,
        is_cisa_kev=True,
        epss_score=0.9421,
        first_detected_at=datetime.now(timezone.utc),
    )

    with patch("services.mod04_disk_scanner.cmd.scanner_worker.main.WorkloadRepository.list_vulnerabilities", return_value=[mock_vuln]):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            res = await client.get("/api/v1/workloads/vulnerabilities?only_cisa_kev=true")
            assert res.status_code == 200
            items = res.json()
            assert len(items) == 1
            assert items[0]["cve_id"] == "CVE-2022-0778"
            assert items[0]["is_cisa_kev"] is True

    app.dependency_overrides.clear()

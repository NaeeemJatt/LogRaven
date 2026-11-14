"""API integration tests for Module 05: eBPF Runtime Reachability Sensor & Container Drift."""

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
from services.mod05_ebpf_sensor.internal.repository.models import ContainerDriftAlert, WorkloadRuntimeReachability


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="ebpf-sec@lograven.io",
        name="Runtime Security Engineer",
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
async def test_ingest_sensor_telemetry_clean_execution(test_user, mock_db):
    """Verifies /api/v1/sensor/telemetry ingests clean container execution and maps package."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-clean-workload",
        "container_id": "c-prod-nginx-44",
        "pid": 2048,
        "comm": "curl",
        "filename": "/usr/bin/curl",
        "is_container_upper_layer": 0,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/sensor/telemetry", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "PROCESSED"
        assert data["resolved_package"] == "curl"
        assert "7.88.1" in data["resolved_version"]
        assert data["is_container_drift"] is False
        assert data["drift_alert"] is None
        assert data["telemetry_emitted"]["is_loaded_in_memory"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ingest_sensor_telemetry_detects_container_drift(test_user, mock_db):
    """Verifies /api/v1/sensor/telemetry flags execution from upper layer as CONTAINER_DRIFT_EXECUTION."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-compromised-pod",
        "container_id": "c-prod-payment-88",
        "pid": 9912,
        "comm": "nmap",
        "filename": "/var/lib/docker/overlay2/upper/usr/bin/nmap",
        "is_container_upper_layer": 1,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/sensor/telemetry", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "PROCESSED"
        assert data["is_container_drift"] is True
        assert data["drift_alert"] is not None
        assert data["drift_alert"]["alert_type"] == "CONTAINER_DRIFT_EXECUTION"
        assert data["drift_alert"]["severity"] == "CRITICAL"
        assert data["telemetry_emitted"]["is_container_drift"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_check_package_reachability_api(test_user, mock_db):
    """Verifies /api/v1/sensor/reachability queries active in-memory state."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    asset_urn = "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-reachability-test"
    pkg = "openssl"

    with patch(
        "services.mod05_ebpf_sensor.cmd.sensor_daemon.main.ReachabilityRepository.is_package_reachable",
        return_value=True,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            res = await client.get(
                f"/api/v1/sensor/reachability?asset_urn={asset_urn}&package_name={pkg}",
            )
            assert res.status_code == 200
            data = res.json()
            assert data["asset_urn"] == asset_urn
            assert data["package_name"] == pkg
            assert data["is_loaded_in_memory"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_container_drift_alerts_api(test_user, mock_db):
    """Verifies /api/v1/sensor/drift-alerts returns list of detected drift events."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    now = datetime.now(timezone.utc)
    mock_alert = ContainerDriftAlert(
        id=uuid.uuid4(),
        asset_urn="urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-drift-01",
        container_id="c-drift-881",
        binary_path="/upper/bin/miner",
        overlayfs_layer="upperdir",
        process_pid=7711,
        comm="miner",
        severity="CRITICAL",
        detected_at=now,
    )

    with patch(
        "services.mod05_ebpf_sensor.cmd.sensor_daemon.main.ReachabilityRepository.list_drift_alerts",
        return_value=[mock_alert],
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            res = await client.get("/api/v1/sensor/drift-alerts")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            assert data[0]["container_id"] == "c-drift-881"
            assert data[0]["binary_path"] == "/upper/bin/miner"
            assert data[0]["severity"] == "CRITICAL"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sensor_governor_health_api(test_user):
    """Verifies /api/v1/sensor/health reports CPU <= 1.5% and RAM <= 64 MB compliance."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.get("/api/v1/sensor/health")
        assert res.status_code == 200
        data = res.json()
        assert data["cpu_usage_pct"] <= 1.5
        assert data["ram_usage_mb"] <= 64.0
        assert data["is_compliant"] is True

    app.dependency_overrides.clear()

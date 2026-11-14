"""Integration tests for Container Drift Detection (TC-MOD5-002, FR-MOD5-03)."""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.mod05_ebpf_sensor.cmd.sensor_daemon.main import process_execution_event
from services.mod05_ebpf_sensor.internal.drift_detector.overlayfs_checker import OverlayFSChecker
from services.mod05_ebpf_sensor.internal.mapper.proc_resolver import ProcessResolver
from services.mod05_ebpf_sensor.internal.telemetry_exporter.reachability_publisher import ReachabilityPublisher


def test_tc_mod5_002_container_drift_execution_alert():
    """TC-MOD5-002: In a running container, simulate execution of newly installed binary 'nmap'.
    
    Pass Criteria: Sensor detects binary originating from writable upperdir;
    emits alert CONTAINER_DRIFT_EXECUTION within 1 second.
    """
    checker = OverlayFSChecker()

    # Simulated eBPF execution event of 'nmap' installed post-deployment into container's writable upper layer
    event = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-0a1b2c3d4e5f6g7h8",
        "container_id": "container_prod_payments_8831",
        "pid": 4821,
        "comm": "nmap",
        "filename": "/var/lib/docker/overlay2/deadbeef1234/upper/usr/bin/nmap",
        "is_container_upper_layer": 1,
        "timestamp": time.time(),
    }

    start = time.perf_counter()
    alert = checker.inspect_exec_event(event)
    elapsed_s = time.perf_counter() - start

    assert alert is not None, "Failed to detect container drift"
    assert alert["alert_type"] == "CONTAINER_DRIFT_EXECUTION"
    assert alert["severity"] == "CRITICAL"
    assert alert["container_id"] == "container_prod_payments_8831"
    assert alert["binary_path"] == "/var/lib/docker/overlay2/deadbeef1234/upper/usr/bin/nmap"
    assert alert["overlayfs_layer"] == "upperdir"
    assert "Unauthorized binary execution from mutable container layer" in alert["description"]
    assert elapsed_s < 1.0, f"Detection took {elapsed_s:.4f}s, expected < 1.0s"


def test_immutable_base_image_binary_not_drift():
    """Verifies that legitimate base image binaries from lower layers are not flagged as drift."""
    checker = OverlayFSChecker()

    event = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-0a1b2c3d4e5f6g7h8",
        "container_id": "container_prod_payments_8831",
        "pid": 1024,
        "comm": "nginx",
        "filename": "/usr/sbin/nginx",
        "is_container_upper_layer": 0,
    }

    alert = checker.inspect_exec_event(event)
    assert alert is None, "Legitimate base image execution should not trigger drift alert"


def test_host_level_binary_not_flagged_as_container_drift():
    """Host execution (without container_id) must never emit container drift alerts."""
    checker = OverlayFSChecker()

    event = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-0a1b2c3d4e5f6g7h8",
        "container_id": None,
        "pid": 55,
        "comm": "apt-get",
        "filename": "/tmp/installer.sh",
        "is_container_upper_layer": 1,
    }

    alert = checker.inspect_exec_event(event)
    assert alert is None, "Host execution should not trigger container drift alert"


@pytest.mark.asyncio
async def test_full_pipeline_drift_and_telemetry_emission():
    """Verifies full execution pipeline: drift detection + reachability record + telemetry emission."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    publisher = ReachabilityPublisher()
    resolver = ProcessResolver()
    resolver.register_path("/tmp/nmap", "nmap", "7.93+dfsg1-1")

    event = {
        "asset_urn": "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-0a1b2c3d4e5f6g7h8",
        "container_id": "c-4421-prod",
        "pid": 8891,
        "comm": "nmap",
        "filename": "/tmp/nmap",
        "is_container_upper_layer": 1,
    }

    response = await process_execution_event(
        session=session,
        event=event,
        resolver=resolver,
        drift_checker=OverlayFSChecker(),
        publisher=publisher,
    )

    assert response.status == "PROCESSED"
    assert response.is_container_drift is True
    assert response.drift_alert is not None
    assert response.drift_alert["alert_type"] == "CONTAINER_DRIFT_EXECUTION"
    assert response.resolved_package == "nmap"
    assert response.resolved_version == "7.93+dfsg1-1"
    assert response.telemetry_emitted is not None
    assert response.telemetry_emitted["is_loaded_in_memory"] is True
    assert response.telemetry_emitted["is_container_drift"] is True
    assert len(publisher.published_events) == 1


"""Chaos and Resilience tests for Two-Tier Ephemeral Snapshot Cleanup (TC-MOD4-004)."""

import time
from unittest.mock import AsyncMock
import pytest

from services.mod04_disk_scanner.internal.snapshot_mgr.cleaner import SnapshotCleaner


@pytest.mark.asyncio
async def test_tc_mod4_004_crash_recovery_orphan_sweep():
    """TC-MOD4-004: Simulate scanner crash during volume inspection.
    
    Pass Criteria: Ephemeral cleaner sweep detects orphaned volume/snapshot on restart
    and purges within 60s without leaking AWS EBS billing costs.
    """
    cleaner = SnapshotCleaner(ttl_seconds=300)
    mock_cloud_client = AsyncMock()

    # 1. Scanner worker registers 2 snapshots before an unexpected crash
    snap_1 = "snap-crash-001"
    snap_2 = "snap-crash-002"
    cleaner.register_resource(snap_1, provider="aws", details={"volume": "vol-123"})
    cleaner.register_resource(snap_2, provider="aws", details={"volume": "vol-456"})

    # Simulate passage of time past TTL (e.g., 305 seconds while worker was dead)
    cleaner._tracked_resources[snap_1]["created_at"] = time.time() - 310
    cleaner._tracked_resources[snap_2]["created_at"] = time.time() - 320

    # 2. Worker restarts and runs startup sweep
    purged = await cleaner.sweep_orphans(cloud_client=mock_cloud_client)

    # 3. Assert both orphaned snapshots were deleted immediately on recovery
    assert len(purged) == 2
    assert snap_1 in purged
    assert snap_2 in purged
    assert cleaner._tracked_resources == {}
    assert mock_cloud_client.delete_snapshot.await_count == 2


@pytest.mark.asyncio
async def test_force_cleanup_all_active_ephemeral_resources():
    """Verifies force sweep immediately cleans all tracked ephemeral resources."""
    cleaner = SnapshotCleaner(ttl_seconds=300)
    cleaner.register_resource("snap-active-001")
    cleaner.register_resource("snap-active-002")

    purged = await cleaner.sweep_orphans(force_all=True)
    assert len(purged) == 2
    assert len(cleaner.deleted_history) == 2
    assert len(cleaner._tracked_resources) == 0


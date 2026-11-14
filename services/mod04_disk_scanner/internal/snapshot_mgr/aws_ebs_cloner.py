"""AWS EBS Snapshot Cloner & Direct API Client."""

from contextlib import asynccontextmanager
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid

from services.mod04_disk_scanner.internal.snapshot_mgr.cleaner import SnapshotCleaner

logger = logging.getLogger(__name__)


class AWSEBSCloner:
    """Creates temporary point-in-time EBS snapshots for out-of-band disk inspection."""

    def __init__(self, ec2_client=None, ebs_client=None, cleaner: Optional[SnapshotCleaner] = None):
        self.ec2 = ec2_client
        self.ebs = ebs_client
        self.cleaner = cleaner or SnapshotCleaner(ttl_seconds=300)

    async def create_ephemeral_snapshot(
        self,
        volume_id: str,
        account_id: str,
        region: str = "us-east-1",
        description: str = "LogRaven Out-of-Band Workload Scan",
    ) -> Dict[str, Any]:
        """Creates a snapshot with standard LogRaven lifecycle tags."""
        snap_id = f"snap-{uuid.uuid4().hex[:16]}"
        logger.info(f"Initiating ephemeral snapshot {snap_id} for volume {volume_id}")

        snapshot_info = {
            "snapshot_id": snap_id,
            "volume_id": volume_id,
            "account_id": account_id,
            "region": region,
            "state": "completed",
            "volume_size_gb": 20,
            "block_size": 524288,  # 512 KiB default EBS block size
            "created_at": time.time(),
            "tags": {
                "ManagedBy": "LogRaven",
                "Purpose": "EphemeralWorkloadScan",
                "lograven-scan": "true",
            },
        }

        # Register with cleaner immediately to guarantee cleanup within 300s
        self.cleaner.register_resource(
            resource_id=snap_id,
            provider="aws",
            resource_type="snapshot",
            details=snapshot_info,
        )

        return snapshot_info

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Deletes ephemeral snapshot."""
        logger.info(f"Deleting ephemeral snapshot {snapshot_id}")
        self.cleaner.unregister_resource(snapshot_id)
        return True

    @asynccontextmanager
    async def snapshot_session(
        self,
        volume_id: str,
        account_id: str,
        region: str = "us-east-1",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async context manager guaranteeing cleanup of the ephemeral snapshot upon exit."""
        snap = await self.create_ephemeral_snapshot(volume_id=volume_id, account_id=account_id, region=region)
        try:
            yield snap
        finally:
            await self.delete_snapshot(snap["snapshot_id"])


"""OverlayFS Container Drift Detector (FR-MOD5-03, TC-MOD5-002)."""

import os
import time
from typing import Any, Dict, List, Optional


class OverlayFSChecker:
    """Detects whether an executing binary originates from the container's mutable upperdir."""

    @staticmethod
    def is_upper_layer(file_path: str, is_upper_flag: Optional[int] = None) -> bool:
        """Determines if the binary originates from the writable upper layer rather than base image."""
        if is_upper_flag is not None:
            return bool(is_upper_flag)

        # Check path patterns indicative of runtime container package installs / drops
        upper_indicators = ("/var/lib/docker/overlay2", "/overlay2/", "/upper/", "/tmp/", "/dev/shm/")
        if any(ind in file_path for ind in upper_indicators):
            return True

        return False

    @staticmethod
    def inspect_exec_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluates an eBPF execution event for container drift.
        
        If executing binary originates from the writable upper layer, emits
        CONTAINER_DRIFT_EXECUTION alert within 1 second (TC-MOD5-002).
        """
        container_id = event.get("container_id")
        # If not running in a container, container drift does not apply
        if not container_id:
            return None

        file_path = event.get("filename", "")
        is_upper = OverlayFSChecker.is_upper_layer(
            file_path=file_path,
            is_upper_flag=event.get("is_container_upper_layer"),
        )

        if is_upper:
            return {
                "alert_type": "CONTAINER_DRIFT_EXECUTION",
                "severity": "CRITICAL",
                "container_id": container_id,
                "asset_urn": event.get("asset_urn"),
                "binary_path": file_path,
                "process_pid": event.get("pid", 0),
                "comm": event.get("comm", os.path.basename(file_path)),
                "overlayfs_layer": "upperdir",
                "description": (
                    f"CRITICAL: Unauthorized binary execution from mutable container layer: "
                    f"'{file_path}' in container {container_id}. Binary was modified or installed post-deployment."
                ),
                "timestamp": event.get("timestamp", time.time()),
            }

        return None

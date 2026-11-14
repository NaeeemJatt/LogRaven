"""Reachability Telemetry Publisher: Emits in-memory package execution signals."""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReachabilityPublisher:
    """Publishes runtime reachability state to topic workload.runtime.reachability."""

    def __init__(self, kafka_producer=None):
        self.producer = kafka_producer
        self.published_events: List[Dict[str, Any]] = []

    async def emit_reachability(
        self,
        asset_urn: str,
        package_name: str,
        library_path: str,
        container_id: Optional[str] = None,
        is_container_drift: bool = False,
    ) -> Dict[str, Any]:
        """Constructs and publishes a reachability signal."""
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "asset_urn": asset_urn,
            "container_id": container_id,
            "package_name": package_name,
            "library_path": library_path,
            "is_loaded_in_memory": True,
            "is_container_drift": is_container_drift,
            "first_executed_at": now_iso,
        }

        self.published_events.append(payload)

        if self.producer:
            try:
                await self.producer.send_and_wait(
                    "workload.runtime.reachability",
                    json.dumps(payload).encode("utf-8"),
                )
            except Exception as e:
                logger.warning(f"Failed to publish reachability telemetry: {e}")

        return payload

"""Event Publisher for CSPM Asset Mutations and Tombstoning (FR-MOD2-04, TC-MOD2-003, TC-MOD2-005)."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class AssetEventPublisher:
    """Publishes AssetMutatedEvent to topic `cspm.asset.mutated` on config drift."""

    def __init__(self, kafka_producer: Optional[Any] = None, topic: str = "cspm.asset.mutated"):
        self.producer = kafka_producer
        self.topic = topic
        self.published_events: List[Dict[str, Any]] = []

    async def emit_mutation(
        self,
        tenant_id: str,
        urn: str,
        change_type: str, # "CREATED", "CONFIG_DRIFT", "DELETED"
        current_sha256: str,
        previous_sha256: Optional[str] = None,
        mutated_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Constructs and publishes an AssetMutatedEvent."""
        event_payload = {
            "event_id": f"evt-{uuid.uuid4()}",
            "tenant_id": str(tenant_id),
            "urn": urn,
            "change_type": change_type,
            "previous_sha256": previous_sha256,
            "current_sha256": current_sha256,
            "mutated_paths": mutated_paths or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Record event in local log
        self.published_events.append(event_payload)

        # If real Kafka/Redpanda producer is attached
        if self.producer:
            try:
                msg_bytes = json.dumps(event_payload).encode("utf-8")
                if hasattr(self.producer, "send"):
                    self.producer.send(self.topic, key=urn.encode("utf-8"), value=msg_bytes)
                elif hasattr(self.producer, "publish"):
                    await self.producer.publish(self.topic, key=urn, value=msg_bytes)
            except Exception:
                pass

        return event_payload


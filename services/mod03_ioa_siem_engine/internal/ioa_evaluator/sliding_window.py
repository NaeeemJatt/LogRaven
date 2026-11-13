"""Redis-backed 15-minute sliding window stateful IOA sequence evaluator."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from services.mod03_ioa_siem_engine.internal.ioa_evaluator.rules.enum_rules import EnumerationBurstRule
from services.mod03_ioa_siem_engine.internal.ioa_evaluator.rules.persistence_rules import PersistenceRule
from services.mod03_ioa_siem_engine.internal.ioa_evaluator.rules.privesc_rules import PrivilegeEscalationRule

logger = logging.getLogger(__name__)


# Defense Evasion single-event triggers
SINGLE_EVENT_DEFENSE_EVASION = {
    "StopLogging": ("IOA-AWS-DEFENSE-001", "AWS CloudTrail Logging Terminated", "CRITICAL", "T1562.001"),
    "DeleteTrail": ("IOA-AWS-DEFENSE-002", "AWS CloudTrail Audit Trail Deleted", "CRITICAL", "T1562.001"),
    "DeleteDetector": ("IOA-AWS-DEFENSE-003", "Amazon GuardDuty Detector Deleted", "CRITICAL", "T1562.001"),
    "UpdateTrail": ("IOA-AWS-DEFENSE-004", "AWS CloudTrail Configuration Modified", "HIGH", "T1562.001"),
}


class SlidingWindowIOAEvaluator:
    """Evaluates real-time events across a 15-minute (900s) sliding window per actor."""

    def __init__(self, redis_client=None, window_seconds: int = 900):
        self.window_seconds = window_seconds
        self.redis = redis_client
        # In-memory sliding buffer: { "tenant_id:actor_arn": [ {event}, ... ] }
        self._mem_store: Dict[str, List[Dict[str, Any]]] = {}

    def _get_key(self, tenant_id: str, actor_user_arn: str) -> str:
        return f"ioa_window:{tenant_id}:{actor_user_arn}"

    async def ingest_and_evaluate(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Appends event to actor's window, evicts expired items, and evaluates sequence & single rules."""
        tenant_id = str(event.get("tenant_id") or "default")
        actor = str(event.get("actor_user_arn") or "unknown-actor")
        now_ts = time.time()

        # Normalise timestamp
        event_dict = dict(event)
        if "timestamp" not in event_dict:
            event_dict["timestamp"] = now_ts

        # 1. Single-event check (Defense Evasion, etc.)
        event_name = event_dict.get("event_name", "")
        if event_name in SINGLE_EVENT_DEFENSE_EVASION:
            rule_id, title, sev, tech = SINGLE_EVENT_DEFENSE_EVASION[event_name]
            return {
                "incident_id": f"ioa-{uuid.uuid4().hex[:12]}",
                "rule_id": rule_id,
                "rule_name": title,
                "severity": sev,
                "mitre_tactic": "DEFENSE_EVASION",
                "mitre_technique": tech,
                "actor_user_arn": actor,
                "account_id": event_dict.get("account_id"),
                "matched_events_count": 1,
                "evidence_events": [event_dict],
                "description": f"Immediate alert: Principal {actor} executed {event_name} to blind security auditing.",
            }

        # 2. Add to sliding window
        window = await self._add_to_window(tenant_id, actor, event_dict, now_ts)

        # 3. Evaluate multi-step rules
        # A. Privilege Escalation (PassRole -> CreateFunction/RunInstances -> Invoke)
        privesc_hit = PrivilegeEscalationRule.evaluate(window)
        if privesc_hit:
            privesc_hit["incident_id"] = f"ioa-{uuid.uuid4().hex[:12]}"
            return privesc_hit

        # B. Persistence (CreateUser/Key -> AttachPolicy)
        persist_hit = PersistenceRule.evaluate(window)
        if persist_hit:
            persist_hit["incident_id"] = f"ioa-{uuid.uuid4().hex[:12]}"
            return persist_hit

        # C. Enumeration Burst (20+ AccessDenied within 60s)
        enum_hit = EnumerationBurstRule.evaluate(window)
        if enum_hit:
            enum_hit["incident_id"] = f"ioa-{uuid.uuid4().hex[:12]}"
            return enum_hit

        return None

    async def _add_to_window(
        self, tenant_id: str, actor: str, event: Dict[str, Any], now_ts: float
    ) -> List[Dict[str, Any]]:
        key = self._get_key(tenant_id, actor)
        cutoff = now_ts - self.window_seconds

        if self.redis is not None:
            try:
                # Add to Redis ZSET: score is timestamp, member is json
                payload = json.dumps(event)
                await self.redis.zadd(key, {payload: now_ts})
                # Evict older than cutoff
                await self.redis.zremrangebyscore(key, "-inf", cutoff)
                await self.redis.expire(key, self.window_seconds)

                # Fetch window
                raw_items = await self.redis.zrange(key, 0, -1)
                return [json.loads(item) for item in raw_items]
            except Exception as e:
                logger.warning(f"Redis window fallback to in-memory: {e}")

        # In-Memory fallback
        if key not in self._mem_store:
            self._mem_store[key] = []

        # Evict old events
        self._mem_store[key] = [e for e in self._mem_store[key] if e.get("timestamp", 0) >= cutoff]
        self._mem_store[key].append(event)
        return self._mem_store[key]

    def clear(self):
        """Clears in-memory buffer."""
        self._mem_store.clear()


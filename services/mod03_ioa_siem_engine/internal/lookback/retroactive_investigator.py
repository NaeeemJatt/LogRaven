"""Automated 90-Day Retroactive SIEM Investigation Engine.

Executes retroactive lookback queries in ClickHouse ocsf_cloud_activity when
a new high/critical IOM is opened, searching for external IP or unauthorized access.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class ClickHouseLookbackClient:
    """Interface to execute high-throughput analytical lookbacks against ClickHouse."""

    def __init__(self, clickhouse_client=None):
        self.client = clickhouse_client
        # In-memory mock storage for testing and offline environments
        self._in_memory_events: List[Dict[str, Any]] = []

    def seed_events(self, events: List[Dict[str, Any]]):
        """Seeds records into the in-memory log buffer."""
        self._in_memory_events.extend(events)

    async def query_external_activity(
        self,
        tenant_id: str,
        target_resource_urn: str,
        lookback_days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Queries ocsf_cloud_activity for external IP accesses to the specific URN within the lookback window."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        if self.client is not None:
            try:
                query = """
                SELECT event_time, provider, account_id, event_name, actor_user_arn, src_ip, is_external_ip, geo_country
                FROM ocsf_cloud_activity
                WHERE tenant_id = %(tenant_id)s
                  AND target_resource_urn = %(target_urn)s
                  AND is_external_ip = 1
                  AND event_time >= %(cutoff)s
                ORDER BY event_time DESC
                LIMIT 500
                """
                # Execute against ClickHouse
                result = await self.client.execute(
                    query,
                    params={
                        "tenant_id": tenant_id,
                        "target_urn": target_resource_urn,
                        "cutoff": cutoff,
                    },
                )
                return result
            except Exception as e:
                logger.warning(f"ClickHouse query error, falling back to local buffer: {e}")

        # In-memory evaluation
        matches = []
        for e in self._in_memory_events:
            # Check tenant if present
            if str(e.get("tenant_id", tenant_id)) != str(tenant_id):
                continue
            if e.get("target_resource_urn") != target_resource_urn:
                continue
            if int(e.get("is_external_ip", 0)) != 1:
                continue

            # Check time if parseable
            evt_time_raw = e.get("event_time")
            if evt_time_raw:
                try:
                    if isinstance(evt_time_raw, str):
                        dt = datetime.fromisoformat(evt_time_raw.replace("Z", "+00:00"))
                    else:
                        dt = evt_time_raw
                    if dt < cutoff:
                        continue
                except Exception:
                    pass

            matches.append(e)

        return matches


class RetroactiveInvestigator:
    """Automated SIEM investigator attaching activity multipliers to security findings."""

    def __init__(self, clickhouse_client: Optional[ClickHouseLookbackClient] = None):
        self.ch = clickhouse_client or ClickHouseLookbackClient()

    async def investigate_finding(
        self,
        finding: Dict[str, Any],
        tenant_id: Optional[str] = None,
        lookback_days: int = 90,
    ) -> Dict[str, Any]:
        """Performs 90-day lookback for the finding's target URN.
        
        If external read/access records exist:
        - Sets siem_activity_multiplier = 1.5 (FR-MOD3-04, TC-MOD3-004)
        - Attaches evidence access records
        - Elevates effective risk score
        """
        tid = str(tenant_id or finding.get("tenant_id") or uuid.uuid4())
        urn = finding.get("target_resource_urn") or finding.get("urn")
        if not urn:
            return finding

        records = await self.ch.query_external_activity(
            tenant_id=tid,
            target_resource_urn=urn,
            lookback_days=lookback_days,
        )

        investigated = dict(finding)
        investigated["lookback_performed"] = True
        investigated["lookback_window_days"] = lookback_days
        investigated["matched_external_access_count"] = len(records)
        investigated["external_access_records"] = records

        base_score = float(finding.get("base_risk_score", finding.get("severity_score", 7.0)))

        if len(records) > 0:
            investigated["siem_activity_multiplier"] = 1.5
            investigated["active_threat_detected"] = True
            investigated["effective_risk_score"] = min(10.0, round(base_score * 1.5, 2))
            investigated["investigation_summary"] = (
                f"Active external exploitation risk confirmed: {len(records)} external access events "
                f"detected for {urn} over the last {lookback_days} days. Applied 1.5x SIEM multiplier."
            )
        else:
            investigated["siem_activity_multiplier"] = 1.0
            investigated["active_threat_detected"] = False
            investigated["effective_risk_score"] = base_score
            investigated["investigation_summary"] = (
                f"No external IP access detected for {urn} within {lookback_days} days."
            )

        return investigated


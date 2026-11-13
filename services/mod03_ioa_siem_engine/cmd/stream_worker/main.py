"""Module 03: Real-Time IOA Telemetry, OCSF Mapping & SIEM Log Engine.

FastAPI Router and Stream Worker Pipeline.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.models.user import User
from services.mod03_ioa_siem_engine.internal.ioa_evaluator.sliding_window import SlidingWindowIOAEvaluator
from services.mod03_ioa_siem_engine.internal.lookback.retroactive_investigator import (
    ClickHouseLookbackClient,
    RetroactiveInvestigator,
)
from services.mod03_ioa_siem_engine.internal.mutation_bridge.resource_extractor import MutationBridge
from services.mod03_ioa_siem_engine.internal.parser.ocsf_mapper import OCSFMapper
from services.mod03_ioa_siem_engine.internal.parser.schema_validator import OCSFCloudActivityEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 03: IOA & SIEM Engine"])

# Shared engine instances
_sliding_evaluator = SlidingWindowIOAEvaluator()
_mutation_bridge = MutationBridge()
_lookback_client = ClickHouseLookbackClient()
_retro_investigator = RetroactiveInvestigator(clickhouse_client=_lookback_client)


# ── Request / Response Models ─────────────────────────────────────────────

class IngestStreamEventRequest(BaseModel):
    provider: Optional[str] = "aws"
    raw_event: Dict[str, Any]


class IngestStreamEventResponse(BaseModel):
    status: str
    ocsf_event: Dict[str, Any]
    ioa_incident: Optional[Dict[str, Any]] = None
    priority_crawl_job: Optional[Dict[str, Any]] = None


class InvestigateFindingRequest(BaseModel):
    finding_id: str
    target_resource_urn: str
    base_risk_score: float = 7.0
    lookback_days: int = 90


class InvestigateFindingResponse(BaseModel):
    finding_id: str
    target_resource_urn: str
    lookback_performed: bool
    lookback_window_days: int
    matched_external_access_count: int
    siem_activity_multiplier: float
    active_threat_detected: bool
    effective_risk_score: float
    investigation_summary: str
    external_access_records: List[Dict[str, Any]]


# ── Pipeline Coordinator ──────────────────────────────────────────────────

async def process_stream_event(
    raw_event: Dict[str, Any],
    tenant_id: str,
    provider: Optional[str] = None,
    evaluator: Optional[SlidingWindowIOAEvaluator] = None,
    bridge: Optional[MutationBridge] = None,
) -> IngestStreamEventResponse:
    """Core stream pipeline: OCSF normalize -> Sliding IOA evaluate -> Mutation bridge re-crawl."""
    ev = evaluator or _sliding_evaluator
    br = bridge or _mutation_bridge

    # 1. Normalize to OCSF v1.2
    ocsf_model = OCSFMapper.map_event(raw_event, tenant_id=tenant_id, provider_hint=provider)
    ocsf_dict = ocsf_model.model_dump()

    # 2. Stateful Sliding-Window IOA check
    ioa_hit = await ev.ingest_and_evaluate(ocsf_dict)

    # 3. Mutation bridge check for targeted re-crawl
    crawl_job = br.extract_and_enqueue(ocsf_dict)

    return IngestStreamEventResponse(
        status="PROCESSED",
        ocsf_event=ocsf_dict,
        ioa_incident=ioa_hit,
        priority_crawl_job=crawl_job,
    )


# ── REST Endpoints ────────────────────────────────────────────────────────

@router.post("/events/stream", response_model=IngestStreamEventResponse)
async def ingest_stream_cloud_event(
    req: IngestStreamEventRequest,
    current_user: User = Depends(get_current_user),
):
    """Ingest raw multi-cloud audit event, normalize to OCSF v1.2, evaluate IOAs, and dispatch mutation crawls."""
    return await process_stream_event(
        raw_event=req.raw_event,
        tenant_id=str(current_user.id),
        provider=req.provider,
    )


@router.post("/investigate", response_model=InvestigateFindingResponse)
async def trigger_retroactive_investigation(
    req: InvestigateFindingRequest,
    current_user: User = Depends(get_current_user),
):
    """Run automated 90-day retroactive SIEM lookback for a finding to detect external exploitation."""
    result = await _retro_investigator.investigate_finding(
        finding={
            "finding_id": req.finding_id,
            "target_resource_urn": req.target_resource_urn,
            "base_risk_score": req.base_risk_score,
        },
        tenant_id=str(current_user.id),
        lookback_days=req.lookback_days,
    )
    return InvestigateFindingResponse(**result)


@router.get("/rules")
async def list_ioa_detection_rules(
    current_user: User = Depends(get_current_user),
):
    """List active MITRE ATT&CK real-time IOA rules and detection coverage."""
    return {
        "tactics_covered": [
            "PRIVILEGE_ESCALATION",
            "PERSISTENCE",
            "DEFENSE_EVASION",
            "ENUMERATION",
        ],
        "active_rules": [
            {
                "rule_id": "IOA-AWS-PRIVESC-004",
                "name": "AWS IAM PassRole Privilege Escalation to Compute",
                "severity": "CRITICAL",
                "tactic": "PRIVILEGE_ESCALATION",
                "technique": "T1078.004",
            },
            {
                "rule_id": "IOA-AWS-PERSIST-002",
                "name": "Backdoor Account Creation with Admin Policy Attachment",
                "severity": "CRITICAL",
                "tactic": "PERSISTENCE",
                "technique": "T1098",
            },
            {
                "rule_id": "IOA-CLOUD-ENUM-011",
                "name": "Automated Cloud API Enumeration Burst",
                "severity": "HIGH",
                "tactic": "ENUMERATION",
                "technique": "T1580",
            },
            {
                "rule_id": "IOA-AWS-DEFENSE-001",
                "name": "AWS CloudTrail Logging Terminated",
                "severity": "CRITICAL",
                "tactic": "DEFENSE_EVASION",
                "technique": "T1562.001",
            },
        ],
    }

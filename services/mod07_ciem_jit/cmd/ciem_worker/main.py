"""Module 07: CIEM Effective Permission AST Resolver & ChatOps JIT Broker.

FastAPI Router and CIEM Analysis Coordinator (PRD-MOD-07).
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod07_ciem_jit.internal.ast_resolver.scp_boundary_filter import EffectivePermissionResolver
from services.mod07_ciem_jit.internal.chatops_jit.lease_scheduler import JITLeaseScheduler
from services.mod07_ciem_jit.internal.chatops_jit.slack_handler import SlackJITHandler
from services.mod07_ciem_jit.internal.repository.ciem_repo import CIEMRepository
from services.mod07_ciem_jit.internal.toxic_matrix.combination_checker import ToxicCombinationChecker
from services.mod07_ciem_jit.internal.toxic_matrix.privesc_catalog import PRIVESC_CATALOG
from services.mod07_ciem_jit.internal.usage_analyzer.least_privilege_builder import LeastPrivilegeBuilder
from services.mod07_ciem_jit.internal.usage_analyzer.usage_diff import UsageDiffAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 07: CIEM & JIT Access"])

# Global scheduler instance
_lease_scheduler = JITLeaseScheduler()


# ── Request / Response Models ─────────────────────────────────────────────

class EvaluatePermissionsRequest(BaseModel):
    principal_arn: str
    provider: str = "aws"
    identity_policies: List[Dict[str, Any]]
    permission_boundaries: Optional[List[Dict[str, Any]]] = None
    scp_policies: Optional[List[Dict[str, Any]]] = None
    resource_policies: Optional[List[Dict[str, Any]]] = None
    session_policies: Optional[List[Dict[str, Any]]] = None


class RightSizePolicyRequest(BaseModel):
    principal_arn: str
    granted_actions: List[str]
    used_actions_90d: List[str]
    resource_arn: str = "*"


class RequestJITLeaseRequest(BaseModel):
    target_role_arn: str
    duration_minutes: int = Field(60, ge=15, le=480)
    justification: str


class ApproveJITLeaseRequest(BaseModel):
    lease_id: str


class RevokeJITLeaseRequest(BaseModel):
    lease_id: str
    reason: Optional[str] = "Administrative revocation"


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/evaluate-permissions")
async def evaluate_permissions(
    req: EvaluatePermissionsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculates 5-layer effective permissions and detects toxic privilege escalation vectors."""
    # 1. Resolve 5-layer AST math
    resolution = EffectivePermissionResolver.resolve_effective_permissions(
        identity_policies=req.identity_policies,
        permission_boundaries=req.permission_boundaries,
        scp_policies=req.scp_policies,
        resource_policies=req.resource_policies,
        session_policies=req.session_policies,
    )

    effective_actions = resolution["effective_actions"]

    # 2. Check toxic privilege escalation vectors
    toxic_result = ToxicCombinationChecker.evaluate_principal_actions(
        granted_actions=effective_actions,
        provider=req.provider,
    )

    # 3. Persist record to DB
    try:
        await CIEMRepository.upsert_entitlement(
            session=db,
            principal_arn=req.principal_arn,
            provider=req.provider,
            granted_actions=effective_actions,
            used_actions_90d=[],
            is_admin=resolution["is_admin"],
            has_toxic_combinations=toxic_result["has_toxic_combinations"],
            toxic_vectors=toxic_result["vector_ids"],
            tenant_id=current_user.id if current_user else None,
        )
        await db.commit()
    except Exception as e:
        logger.debug(f"DB upsert entitlement skipped in mock: {e}")

    return {
        "principal_arn": req.principal_arn,
        "provider": req.provider,
        "effective_actions_count": resolution["effective_actions_count"],
        "effective_actions": effective_actions,
        "is_admin": resolution["is_admin"],
        "scp_override_applied": resolution["scp_override_applied"],
        "has_toxic_combinations": toxic_result["has_toxic_combinations"],
        "toxic_vectors": toxic_result["toxic_vectors"],
    }


@router.post("/right-size")
async def right_size_entitlement(
    req: RightSizePolicyRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyzes 90-day usage and emits pruned least-privilege replacement IAM policy."""
    diff = UsageDiffAnalyzer.calculate_diff(
        granted_actions=req.granted_actions,
        used_actions_90d=req.used_actions_90d,
    )

    policy = LeastPrivilegeBuilder.build_replacement_policy(
        used_actions=req.used_actions_90d,
        policy_name=f"Pruned-{req.principal_arn.split('/')[-1]}",
        resource_arn=req.resource_arn,
    )

    return {
        "principal_arn": req.principal_arn,
        "usage_diff": diff,
        "recommended_policy": policy,
    }


@router.post("/jit/request")
async def request_jit_access(
    req: RequestJITLeaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submits a JIT ephemeral access lease request."""
    lease_id = uuid.uuid4()
    lease_record = _lease_scheduler.request_lease(
        requester_email=current_user.email,
        target_role_arn=req.target_role_arn,
        duration_minutes=req.duration_minutes,
        justification=req.justification,
        lease_id=lease_id,
    )

    slack_blocks = SlackJITHandler.create_request_blocks(
        lease_id=lease_id,
        requester_email=current_user.email,
        target_role_arn=req.target_role_arn,
        duration_minutes=req.duration_minutes,
        justification=req.justification,
    )

    try:
        await CIEMRepository.create_jit_lease(
            session=db,
            requester_email=current_user.email,
            target_role_arn=req.target_role_arn,
            justification=req.justification,
            duration_minutes=req.duration_minutes,
            tenant_id=current_user.id,
        )
        await db.commit()
    except Exception:
        pass

    return {
        "status": "REQUESTED",
        "lease": lease_record,
        "slack_notification": slack_blocks,
    }


@router.post("/jit/approve")
async def approve_jit_access(
    req: ApproveJITLeaseRequest,
    current_user: User = Depends(get_current_user),
):
    """Approves and activates a JIT lease, minting ephemeral STS session token."""
    try:
        activated = _lease_scheduler.approve_and_activate_lease(
            lease_id=req.lease_id,
            approver_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "status": "ACTIVE",
        "lease": activated,
    }


@router.post("/jit/revoke")
async def revoke_jit_access(
    req: RevokeJITLeaseRequest,
    current_user: User = Depends(get_current_user),
):
    """Immediately revokes an active JIT lease and invalidates STS token."""
    try:
        revoked = _lease_scheduler.revoke_lease_immediately(
            lease_id=req.lease_id,
            reason=req.reason or "Admin revocation",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "status": "REVOKED",
        "lease": revoked,
    }


@router.get("/jit/leases")
async def list_jit_leases(
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Lists current JIT leases and executes auto-sweep on expired leases."""
    _lease_scheduler.sweep_expired_leases()
    leases = list(_lease_scheduler.active_leases.values())
    if status_filter:
        leases = [l for l in leases if l["status"] == status_filter]
    return leases


@router.get("/toxic-vectors")
async def list_privilege_escalation_vectors(
    current_user: User = Depends(get_current_user),
):
    """Returns the catalog of 21 cloud privilege escalation vectors."""
    return [
        {
            "id": v.id,
            "cloud_provider": v.cloud_provider,
            "title": v.title,
            "severity": v.severity,
            "required_actions": v.required_actions,
            "description": v.description,
            "mitigation": v.mitigation,
        }
        for v in PRIVESC_CATALOG
    ]

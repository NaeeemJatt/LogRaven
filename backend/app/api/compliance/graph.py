"""API routes for Attack Path & Cloud Asset Relationship Graph."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.compliance.graph.builder import build_attack_path_graph
from app.compliance.graph.schemas import AttackPathGraph
from app.dependencies import get_current_user, get_db
from app.models.soc2_audit import AuditJob, CloudAccount
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/compliance/graph", tags=["compliance-graph"])


@router.get("/audits/{audit_id}", response_model=AttackPathGraph)
async def get_audit_attack_path_graph(
    audit_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the interactive Attack Path & Asset Relationship Graph for an audit."""
    stmt = (
        select(AuditJob)
        .options(selectinload(AuditJob.results))
        .where(AuditJob.id == audit_id)
    )
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit job {audit_id} not found.",
        )

    # Detect cloud provider from role_arn or account
    provider = "aws"
    role_arn = getattr(job, "role_arn", "") or ""
    if role_arn.startswith("gcp:"):
        provider = "gcp"
    elif role_arn.startswith("azure:"):
        provider = "azure"

    # If job has no results or signals yet, return empty/baseline graph
    return build_attack_path_graph(job.evidence_signals or {}, job.results or [], provider=provider)


@router.get("/accounts/{account_id}", response_model=AttackPathGraph)
async def get_account_attack_path_graph(
    account_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the Attack Path Graph for the latest audit of a registered cloud account."""
    acc_stmt = select(CloudAccount).where(
        CloudAccount.id == account_id,
        CloudAccount.user_id == current_user.id,
    )
    acc_res = await db.execute(acc_stmt)
    account = acc_res.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cloud account not found.",
        )

    provider = (getattr(account, "provider", None) or "aws").lower().strip()

    # Find latest completed audit for this account
    stmt = (
        select(AuditJob)
        .options(selectinload(AuditJob.results))
        .where(
            AuditJob.cloud_account_id == account_id,
            AuditJob.status == "complete",
        )
        .order_by(desc(AuditJob.created_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        # Return baseline graph with account metadata
        return build_attack_path_graph({}, [], provider=provider)

    return build_attack_path_graph(job.evidence_signals or {}, job.results or [], provider=provider)

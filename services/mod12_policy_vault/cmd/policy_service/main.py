"""Module 12: Visual-to-Rego Studio, Dual-Engine Suppressions, & Cryptographic Audit Vault.

FastAPI Router and Policy Service Coordinator (PRD-MOD-12).
"""

import base64
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod12_policy_vault.internal.audit_vault.manifest_signer import ManifestSigner
from services.mod12_policy_vault.internal.rego_studio.rego_compiler import RegoCompiler
from services.mod12_policy_vault.internal.repository.policy_repo import PolicyVaultRepository
from services.mod12_policy_vault.internal.suppression_engine.boolean_evaluator import (
    BooleanSuppressionEvaluator,
    FindingContext,
    SuppressionRuleData,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 12: Visual-to-Rego Studio & Audit Vault"])


# ── Request / Response Models ─────────────────────────────────────────────

class CompileRegoRequest(BaseModel):
    rule_id: str
    resource_type: str = "aws_s3_bucket"
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None
    package_name: str = "lograven.rules.custom"


class EvaluateSuppressionRequest(BaseModel):
    finding_type: str
    account_id: str
    region: str
    tags: Dict[str, str] = Field(default_factory=dict)
    asset_urn: Optional[str] = None


class CreateSuppressionRuleRequest(BaseModel):
    name: str
    justification: str
    approver: str
    finding_type: Optional[str] = None
    account_ids: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    tag_filters: Dict[str, str] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class CreateCustomRuleRequest(BaseModel):
    rule_id: str
    name: str
    resource_type: str
    visual_ast: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    severity: str = "HIGH"
    message: Optional[str] = None


class CreateVaultPackageRequest(BaseModel):
    package_name: str = "compliance_evidence_vault"
    files: Dict[str, str] = Field(default_factory=dict)  # filename -> text content or b64


class VerifyVaultPackageRequest(BaseModel):
    package_base64: str


# ── REST API Endpoints ───────────────────────────────────────────────────

@router.post("/compile")
async def compile_visual_ast(
    req: CompileRegoRequest,
    current_user: User = Depends(get_current_user),
):
    """Compiles visual rule condition AST into valid Open Policy Agent (OPA) Rego policy code."""
    rego_code = RegoCompiler.compile_rule(
        rule_id=req.rule_id,
        resource_type=req.resource_type,
        conditions=req.conditions,
        message=req.message,
        package_name=req.package_name,
    )
    return {
        "rule_id": req.rule_id,
        "resource_type": req.resource_type,
        "rego_code": rego_code,
    }


@router.post("/suppressions/evaluate")
async def evaluate_finding_suppression(
    req: EvaluateSuppressionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Evaluates finding against active suppression rules using CrowdStrike Boolean evaluation."""
    active_db_rules = await PolicyVaultRepository.list_active_suppressions(db)

    # Convert to evaluation domain objects
    rule_objects = [
        SuppressionRuleData(
            rule_id=str(r.id),
            name=r.name,
            status=r.status,
            finding_type=r.finding_type,
            account_ids=r.account_ids,
            regions=r.regions,
            tag_filters=r.tag_filters,
            expires_at=r.expires_at,
            justification=r.justification,
        )
        for r in active_db_rules
    ]

    finding_ctx = FindingContext(
        finding_type=req.finding_type,
        account_id=req.account_id,
        region=req.region,
        tags=req.tags,
        asset_urn=req.asset_urn,
    )

    is_suppressed, matched_rule = BooleanSuppressionEvaluator.is_finding_suppressed(
        finding=finding_ctx,
        rules=rule_objects,
    )

    return {
        "is_suppressed": is_suppressed,
        "matched_rule_id": matched_rule.rule_id if matched_rule else None,
        "matched_rule_name": matched_rule.name if matched_rule else None,
        "justification": matched_rule.justification if matched_rule else None,
    }


@router.post("/suppressions/sweep")
async def sweep_expired_suppressions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transitions any active suppression rule where now() > expires_at to 'EXPIRED' status."""
    expired_count = await PolicyVaultRepository.sweep_expired_suppressions(db)
    await db.commit()
    return {
        "status": "SUCCESS",
        "expired_count": expired_count,
        "swept_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/suppressions")
async def create_suppression(
    req: CreateSuppressionRuleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new scoped suppression rule."""
    tenant_id = getattr(current_user, "tenant_id", None)
    rule = await PolicyVaultRepository.create_suppression_rule(
        session=db,
        name=req.name,
        justification=req.justification,
        approver=req.approver,
        finding_type=req.finding_type,
        account_ids=req.account_ids,
        regions=req.regions,
        tag_filters=req.tag_filters,
        expires_at=req.expires_at,
        tenant_id=tenant_id,
    )
    await db.commit()
    return {
        "id": str(rule.id),
        "name": rule.name,
        "status": rule.status,
        "finding_type": rule.finding_type,
        "account_ids": rule.account_ids,
        "regions": rule.regions,
        "tag_filters": rule.tag_filters,
        "expires_at": rule.expires_at.isoformat() if rule.expires_at else None,
    }


@router.post("/vault/package")
async def create_vault_package_endpoint(
    req: CreateVaultPackageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates a cryptographically sealed ZIP archive with SHA-256 Merkle root."""
    file_bytes_map: Dict[str, bytes] = {}
    for fname, content in req.files.items():
        file_bytes_map[fname] = content.encode("utf-8")

    zip_bytes = ManifestSigner.create_vault_package(
        files=file_bytes_map,
        package_name=req.package_name,
    )
    verify_res = ManifestSigner.verify_package_integrity(zip_bytes)
    merkle_root = verify_res.get("merkle_root", "")
    manifest = verify_res.get("manifest", {})

    tenant_id = getattr(current_user, "tenant_id", None)
    record = await PolicyVaultRepository.record_vault_package(
        session=db,
        package_name=req.package_name,
        merkle_root_hash=merkle_root,
        file_hashes=manifest.get("file_hashes", {}),
        tenant_id=tenant_id,
    )
    await db.commit()

    return {
        "id": str(record.id),
        "package_name": req.package_name,
        "merkle_root_hash": merkle_root,
        "file_hashes": manifest.get("file_hashes", {}),
        "package_base64": base64.b64encode(zip_bytes).decode("ascii"),
    }


@router.post("/vault/verify")
async def verify_vault_package_endpoint(
    req: VerifyVaultPackageRequest,
    current_user: User = Depends(get_current_user),
):
    """Verifies SHA-256 and Merkle root integrity of an uploaded Evidence Vault ZIP package."""
    try:
        zip_bytes = base64.b64decode(req.package_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 archive payload")

    return ManifestSigner.verify_package_integrity(zip_bytes)


@router.post("/rules")
async def create_custom_rule(
    req: CreateCustomRuleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compiles and saves a visual custom rule."""
    rego_code = RegoCompiler.compile_rule(
        rule_id=req.rule_id,
        resource_type=req.resource_type,
        conditions=req.visual_ast.get("conditions", []),
        message=req.message or req.description,
    )
    tenant_id = getattr(current_user, "tenant_id", None)
    rule = await PolicyVaultRepository.create_custom_rule(
        session=db,
        rule_id=req.rule_id,
        name=req.name,
        resource_type=req.resource_type,
        visual_ast=req.visual_ast,
        rego_code=rego_code,
        description=req.description,
        severity=req.severity,
        tenant_id=tenant_id,
    )
    await db.commit()
    return {
        "id": str(rule.id),
        "rule_id": rule.rule_id,
        "name": rule.name,
        "resource_type": rule.resource_type,
        "rego_code": rule.rego_code,
    }


@router.get("/rules")
async def list_custom_rules(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists custom visual Rego rules."""
    rules = await PolicyVaultRepository.list_custom_rules(db, limit=limit, offset=offset)
    return {
        "total": len(rules),
        "rules": [
            {
                "id": str(r.id),
                "rule_id": r.rule_id,
                "name": r.name,
                "severity": r.severity,
                "resource_type": r.resource_type,
                "rego_code": r.rego_code,
                "is_active": r.is_active,
            }
            for r in rules
        ],
    }

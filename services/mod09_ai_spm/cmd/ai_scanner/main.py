"""Module 09: AI-SPM & Model Context Protocol (MCP) Governance Engine.

FastAPI Router and AI-SPM Coordinator (PRD-MOD-09).
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
from services.mod09_ai_spm.internal.ai_inventory.bedrock_enumerator import BedrockEnumerator
from services.mod09_ai_spm.internal.ai_inventory.sagemaker_enumerator import SageMakerEnumerator
from services.mod09_ai_spm.internal.mcp_auditor.mcp_discoverer import MCPAuditor
from services.mod09_ai_spm.internal.rag_governance.guardrail_evaluator import GuardrailEvaluator
from services.mod09_ai_spm.internal.rag_governance.vector_db_checker import VectorDBChecker
from services.mod09_ai_spm.internal.repository.aispm_repo import AISPMRepository
from services.mod09_ai_spm.internal.weight_scanner.format_verifier import WeightFormatVerifier
from services.mod09_ai_spm.internal.weight_scanner.pickle_scanner import PickleScanner

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 09: AI-SPM & MCP Governance"])


# ── Request / Response Models ─────────────────────────────────────────────

class ScanPickleRequest(BaseModel):
    filename: str = "model.pkl"
    payload_base64: Optional[str] = None
    raw_payload: Optional[str] = None


class AuditMCPRequest(BaseModel):
    server_urn: str
    endpoint_url: str
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    auth_enforced: bool = False
    network_binding: str = "0.0.0.0"


class AuditBedrockRequest(BaseModel):
    endpoint_urn: str
    model_name: str
    guardrail_identifier: Optional[str] = None
    logging_config: Optional[Dict[str, Any]] = None


class AuditVectorDBRequest(BaseModel):
    engine: str = "pinecone"
    endpoint_url: str
    api_key_required: bool = True
    is_in_vpc: bool = True
    tls_enabled: bool = True


class RegisterAIModelRequest(BaseModel):
    asset_urn: str
    provider: str
    model_name: str
    weight_format: str
    has_unsafe_deserialization: bool = False
    guardrails_enabled: bool = False
    prompt_logging_enabled: bool = False
    model_version: Optional[str] = None


# ── REST API Endpoints ───────────────────────────────────────────────────

@router.post("/scan/pickle")
async def scan_pickle_weights(
    req: ScanPickleRequest,
    current_user: User = Depends(get_current_user),
):
    """Scans raw model pickle bytecodes for arbitrary remote code execution without executing them."""
    # 1. Format verification
    format_eval = WeightFormatVerifier.evaluate_format(req.filename)

    # 2. Extract bytes
    data = b""
    if req.payload_base64:
        try:
            data = base64.b64decode(req.payload_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 payload")
    elif req.raw_payload:
        data = req.raw_payload.encode("latin1", errors="ignore")

    # 3. Bytecode scan
    scan_result = PickleScanner.scan_bytes(data)

    return {
        "filename": req.filename,
        "format_evaluation": format_eval,
        "scan_result": scan_result.to_dict(),
        "has_unsafe_deserialization": not scan_result.is_safe,
    }


@router.post("/scan/mcp")
async def audit_mcp_server(
    req: AuditMCPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Audits Model Context Protocol (MCP) server exposure and tool scopes."""
    audit_res = MCPAuditor.audit_server(
        server_urn=req.server_urn,
        endpoint_url=req.endpoint_url,
        tools=req.tools,
        auth_enforced=req.auth_enforced,
        network_binding=req.network_binding,
    )

    # Persist in inventory
    tenant_id = getattr(current_user, "tenant_id", None)
    await AISPMRepository.record_mcp_server(
        session=db,
        server_urn=req.server_urn,
        endpoint_url=req.endpoint_url,
        is_publicly_exposed=audit_res["is_publicly_exposed"],
        auth_enforced=audit_res["auth_enforced"],
        available_tools=req.tools,
        has_high_risk_tools=audit_res["has_high_risk_tools"],
        tenant_id=tenant_id,
    )
    await db.commit()

    return audit_res


@router.post("/scan/bedrock")
async def audit_bedrock_posture(
    req: AuditBedrockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Audits AWS Bedrock endpoint for prompt injection guardrails and CloudWatch invocation logging."""
    audit_res = BedrockEnumerator.evaluate_model_posture(
        endpoint_urn=req.endpoint_urn,
        model_name=req.model_name,
        guardrail_identifier=req.guardrail_identifier,
        logging_config=req.logging_config,
    )

    # Persist in AI inventory
    tenant_id = getattr(current_user, "tenant_id", None)
    await AISPMRepository.record_ai_model(
        session=db,
        asset_urn=req.endpoint_urn,
        provider="aws_bedrock",
        model_name=req.model_name,
        weight_format="safetensors",
        has_unsafe_deserialization=False,
        guardrails_enabled=audit_res["guardrails_enabled"],
        prompt_logging_enabled=audit_res["prompt_logging_enabled"],
        tenant_id=tenant_id,
    )
    await db.commit()

    return audit_res


@router.post("/scan/vector-db")
async def audit_vector_database(
    req: AuditVectorDBRequest,
    current_user: User = Depends(get_current_user),
):
    """Audits RAG vector database for public exposure and transit encryption."""
    return VectorDBChecker.audit_instance(
        engine=req.engine,
        endpoint_url=req.endpoint_url,
        api_key_required=req.api_key_required,
        is_in_vpc=req.is_in_vpc,
        tls_enabled=req.tls_enabled,
    )


@router.get("/models")
async def list_ai_models(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists cataloged AI models in the AI-BOM."""
    models = await AISPMRepository.list_models(db, limit=limit, offset=offset)
    return {
        "total": len(models),
        "models": [
            {
                "id": str(m.id),
                "asset_urn": m.asset_urn,
                "provider": m.provider,
                "model_name": m.model_name,
                "model_version": m.model_version,
                "weight_format": m.weight_format,
                "has_unsafe_deserialization": m.has_unsafe_deserialization,
                "guardrails_enabled": m.guardrails_enabled,
                "prompt_logging_enabled": m.prompt_logging_enabled,
                "scanned_at": m.scanned_at.isoformat() if m.scanned_at else None,
            }
            for m in models
        ],
    }


@router.get("/mcp-servers")
async def list_mcp_servers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists cataloged Model Context Protocol (MCP) servers."""
    servers = await AISPMRepository.list_mcp_servers(db, limit=limit, offset=offset)
    return {
        "total": len(servers),
        "servers": [
            {
                "id": str(s.id),
                "server_urn": s.server_urn,
                "endpoint_url": s.endpoint_url,
                "is_publicly_exposed": s.is_publicly_exposed,
                "auth_enforced": s.auth_enforced,
                "available_tools": s.available_tools,
                "has_high_risk_tools": s.has_high_risk_tools,
                "last_audited_at": s.last_audited_at.isoformat() if s.last_audited_at else None,
            }
            for s in servers
        ],
    }

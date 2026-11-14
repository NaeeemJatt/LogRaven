"""FastAPI Router & Service Entrypoint for Module 01: Multi-Cloud Onboarding & Trust Broker."""

import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod01_onboarding.internal.repository.account_repo import AccountRepository
from services.mod01_onboarding.internal.repository.group_repo import GroupRepository
from services.mod01_onboarding.internal.generators.aws_cloudformation import (
    generate_single_account_cf,
    generate_aws_stackset,
)
from services.mod01_onboarding.internal.generators.terraform_hcl import (
    generate_aws_terraform,
    generate_azure_terraform,
    generate_gcp_terraform,
)
from services.mod01_onboarding.internal.generators.azure_bicep import generate_azure_bicep
from services.mod01_onboarding.internal.sts_broker.aws_sts import STSAssumeRoleBroker
from services.mod01_onboarding.internal.sts_broker.token_cache import TokenCache
from services.mod01_onboarding.internal.validator.policy_simulator import PolicySimulator
from services.mod01_onboarding.internal.validator.event_heartbeat import EventHeartbeatValidator

router = APIRouter(prefix="/cloud-connect", tags=["cloud-connect-onboarding"])

# Shared STS Broker and Token Cache
_token_cache = TokenCache(redis_url=os.environ.get("REDIS_URL"))
_sts_broker = STSAssumeRoleBroker(cache=_token_cache)
_policy_simulator = PolicySimulator()
_heartbeat_validator = EventHeartbeatValidator()


# ── Schemas ──────────────────────────────────────────────────────────────

class ConnectAccountRequest(BaseModel):
    provider: str = Field(default="aws", description="aws, azure, gcp, oci, alibaba, k8s, saas")
    native_account_id: str = Field(..., description="12-digit AWS ID, Azure Sub UUID, GCP Project ID")
    organization_id: Optional[str] = Field(default=None, description="AWS Org ID (o-xxx), Azure Tenant ID, GCP Org ID")
    environment: Optional[str] = Field(default="prod", description="prod, staging, dev")
    cloud_group_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)
    role_arn_or_sp: Optional[str] = Field(default=None, description="Assumable IAM Role ARN or Service Principal ID")


class ConnectAccountResponse(BaseModel):
    account_id: uuid.UUID
    external_id: str
    event_bus_arn: str
    templates: Dict[str, Any]


class ValidateAccountResponse(BaseModel):
    status: str
    iom_ready: bool
    ioa_stream_ready: bool
    missing_permissions: List[str]


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    business_impact: str = Field(default="critical", description="critical, high, medium, low")
    environment: str = Field(default="prod", description="prod, staging, dev")
    account_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)
    tag_filters: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/accounts", response_model=ConnectAccountResponse, status_code=status.HTTP_201_CREATED)
async def register_cloud_account(
    req: ConnectAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register cloud account, generate cryptographic ExternalId, and synthesize onboarding templates."""
    tenant_id = current_user.id
    provider = req.provider.lower().strip()
    role_arn = req.role_arn_or_sp or f"arn:aws:iam::{req.native_account_id}:role/LogRavenCSPMReader"

    # Check if account already exists for tenant
    existing = await AccountRepository.get_by_native_id(db, tenant_id, provider, req.native_account_id)
    if existing:
        ext_id = AccountRepository.get_plaintext_external_id(existing)
        account = existing
    else:
        account, ext_id = await AccountRepository.create_account(
            session=db,
            tenant_id=tenant_id,
            provider=provider,
            native_account_id=req.native_account_id,
            role_arn_or_sp=role_arn,
            organization_id=req.organization_id,
            cloud_group_ids=req.cloud_group_ids,
        )
        await db.commit()
        await db.refresh(account)

    event_bus_arn = f"arn:aws:events:us-east-1:112233445566:event-bus/lr-ingest-{str(tenant_id)[:8]}"

    # Synthesize multi-cloud deployment templates
    tf_hcl = (
        generate_aws_terraform(str(tenant_id), ext_id)
        if provider == "aws"
        else generate_azure_terraform(str(tenant_id), req.native_account_id)
        if provider == "azure"
        else generate_gcp_terraform(str(tenant_id), req.native_account_id)
    )

    bicep = generate_azure_bicep(str(tenant_id)) if provider == "azure" else None

    return ConnectAccountResponse(
        account_id=account.id,
        external_id=ext_id,
        event_bus_arn=event_bus_arn,
        templates={
            "cloudformation_url": f"/api/v1/cloud-connect/templates/cf-stackset.yaml?account_id={account.id}",
            "cloudformation_single_url": f"/api/v1/cloud-connect/templates/cf-single.yaml?account_id={account.id}",
            "terraform_hcl": tf_hcl,
            "bicep_template": bicep,
        },
    )


@router.post("/accounts/{account_id}/validate", response_model=ValidateAccountResponse)
async def validate_cloud_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run pre-flight STS trust verification and iam:SimulatePrincipalPolicy permission probe."""
    account = await AccountRepository.get_by_id(db, account_id, tenant_id=current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    ext_id = AccountRepository.get_plaintext_external_id(account)

    # 1. Assume role via STS Broker (or mock if running in test environment)
    credentials = None
    try:
        credentials, cache_hit = await _sts_broker.get_credentials(
            tenant_id=str(current_user.id),
            account_id=str(account.id),
            role_arn=account.role_arn_or_sp,
            external_id=ext_id,
        )
    except Exception as e:
        err_msg = str(e)
        await AccountRepository.update_status(db, account.id, status="ERROR", missing_permissions=["sts:AssumeRole"])
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "ERR_STS_ASSUME_FAILED",
                "message": f"AWS STS AssumeRole AccessDenied: check ExternalId and Trust Relationship policy ({err_msg}).",
            },
        )

    # 2. Run Policy Simulator
    validation = await _policy_simulator.verify_permissions(
        role_arn=account.role_arn_or_sp,
        session_credentials=credentials,
    )

    new_status = validation.get("status", "CONNECTED")
    missing = validation.get("missing_permissions", [])

    await AccountRepository.update_status(
        db,
        account.id,
        status=new_status,
        missing_permissions=missing,
    )
    await db.commit()

    return ValidateAccountResponse(
        status=new_status,
        iom_ready=validation.get("iom_ready", True),
        ioa_stream_ready=validation.get("ioa_stream_ready", True),
        missing_permissions=missing,
    )


@router.get("/templates/{template_type}")
async def download_template(
    template_type: str,
    account_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download dynamically rendered CloudFormation or Terraform onboarding template."""
    account = await AccountRepository.get_by_id(db, account_id, tenant_id=current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    ext_id = AccountRepository.get_plaintext_external_id(account)
    tenant_str = str(current_user.id)

    if template_type == "cf-stackset.yaml":
        content = generate_aws_stackset(tenant_id=tenant_str, external_id=ext_id)
        media_type = "text/yaml"
    elif template_type == "cf-single.yaml":
        content = generate_single_account_cf(tenant_id=tenant_str, external_id=ext_id)
        media_type = "text/yaml"
    elif template_type in ("terraform.tf", "main.tf"):
        content = generate_aws_terraform(tenant_id=tenant_str, external_id=ext_id)
        media_type = "text/plain"
    elif template_type == "bicep":
        content = generate_azure_bicep(tenant_id=tenant_str)
        media_type = "text/plain"
    else:
        raise HTTPException(status_code=400, detail="Unsupported template type")

    return Response(content=content, media_type=media_type)


@router.post("/groups", status_code=status.HTTP_201_CREATED)
async def create_cloud_group(
    req: CreateGroupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a cloud group with assigned business impact and environment categorization."""
    try:
        group = await GroupRepository.create_group(
            session=db,
            tenant_id=current_user.id,
            name=req.name,
            business_impact=req.business_impact,
            environment=req.environment,
            account_ids=req.account_ids,
            tag_filters=req.tag_filters,
        )
        await db.commit()
        await db.refresh(group)
        return group
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups")
async def list_cloud_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all cloud groups for tenant."""
    groups = await GroupRepository.list_groups(db, tenant_id=current_user.id)
    return groups


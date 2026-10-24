"""API routes for persistent cloud accounts and autonomous scan scheduling."""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.frameworks import list_frameworks
from app.dependencies import get_current_user, get_db
from app.models.soc2_audit import AuditJob, CloudAccount, ComplianceSnapshot
from app.utils.audit import add_audit
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/compliance/accounts", tags=["compliance-accounts"])

_ROLE_ARN_RE = re.compile(r"^arn:aws:iam::\d{12}:role/.+$")


def _calculate_next_run(schedule: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if schedule == "daily":
        return now + timedelta(days=1)
    elif schedule == "weekly":
        return now + timedelta(days=7)
    elif schedule == "monthly":
        return now + timedelta(days=30)
    return None


class CreateCloudAccountRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    provider: str = Field(default="aws")
    role_arn: str | None = Field(default=None, max_length=1024)
    # GCP fields
    gcp_project_id: str | None = Field(default=None, max_length=100)
    gcp_service_account_email: str | None = Field(default=None, max_length=255)
    gcp_workload_identity_pool: str | None = Field(default=None, max_length=255)
    # Azure fields
    azure_tenant_id: str | None = Field(default=None, max_length=100)
    azure_subscription_id: str | None = Field(default=None, max_length=100)
    azure_client_id: str | None = Field(default=None, max_length=100)

    default_frameworks: list[str] = Field(default_factory=lambda: ["soc2"])
    scan_schedule: str = Field(default="weekly")

    @model_validator(mode="after")
    def validate_provider_credentials(self) -> CreateCloudAccountRequest:
        prov = (self.provider or "aws").lower().strip()
        if prov == "aws":
            if not self.role_arn:
                raise ValueError("role_arn is required for AWS accounts")
            if not _ROLE_ARN_RE.match(self.role_arn.strip()):
                raise ValueError("Role ARN must be a valid AWS IAM role ARN, e.g. arn:aws:iam::123456789012:role/LogRavenAuditRole")
        elif prov == "gcp":
            if not self.gcp_project_id:
                raise ValueError("gcp_project_id is required for GCP accounts")
            if not self.gcp_service_account_email:
                raise ValueError("gcp_service_account_email is required for GCP accounts")
        elif prov == "azure":
            if not self.azure_tenant_id:
                raise ValueError("azure_tenant_id is required for Azure accounts")
            if not self.azure_subscription_id:
                raise ValueError("azure_subscription_id is required for Azure accounts")
            if not self.azure_client_id:
                raise ValueError("azure_client_id is required for Azure accounts")
        else:
            raise ValueError(f"Unsupported cloud provider: '{self.provider}'. Must be aws, gcp, or azure.")
        return self

    @field_validator("scan_schedule")
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        if v not in ("none", "daily", "weekly", "monthly"):
            raise ValueError("scan_schedule must be one of: none, daily, weekly, monthly")
        return v

    @field_validator("default_frameworks")
    @classmethod
    def validate_frameworks(cls, v: list[str]) -> list[str]:
        valid_ids = {f.id for f in list_frameworks()}
        for fid in v:
            if fid not in valid_ids:
                raise ValueError(f"Unknown framework: '{fid}'")
        return v or ["soc2"]


class UpdateCloudAccountRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    default_frameworks: list[str] | None = None
    scan_schedule: str | None = None
    role_arn: str | None = None
    gcp_project_id: str | None = None
    gcp_service_account_email: str | None = None
    gcp_workload_identity_pool: str | None = None
    azure_tenant_id: str | None = None
    azure_subscription_id: str | None = None
    azure_client_id: str | None = None

    @field_validator("scan_schedule")
    @classmethod
    def validate_schedule(cls, v: str | None) -> str | None:
        if v is not None and v not in ("none", "daily", "weekly", "monthly"):
            raise ValueError("scan_schedule must be one of: none, daily, weekly, monthly")
        return v


class CloudAccountResponse(BaseModel):
    id: str
    name: str
    provider: str
    role_arn: str | None = None
    account_id: str | None = None
    gcp_project_id: str | None = None
    gcp_service_account_email: str | None = None
    gcp_workload_identity_pool: str | None = None
    azure_tenant_id: str | None = None
    azure_subscription_id: str | None = None
    azure_client_id: str | None = None
    default_frameworks: list[str]
    scan_schedule: str
    next_run_at: str | None = None
    last_scanned_at: str | None = None
    health_status: str
    health_error: str | None = None
    created_at: str
    latest_score_percent: float | None = None


def _serialize_account(account: CloudAccount, latest_score: float | None = None) -> CloudAccountResponse:
    return CloudAccountResponse(
        id=str(account.id),
        name=account.name,
        provider=account.provider or "aws",
        role_arn=account.role_arn,
        account_id=account.account_id,
        gcp_project_id=account.gcp_project_id,
        gcp_service_account_email=account.gcp_service_account_email,
        gcp_workload_identity_pool=account.gcp_workload_identity_pool,
        azure_tenant_id=account.azure_tenant_id,
        azure_subscription_id=account.azure_subscription_id,
        azure_client_id=account.azure_client_id,
        default_frameworks=account.default_frameworks or ["soc2"],
        scan_schedule=account.scan_schedule,
        next_run_at=account.next_run_at.isoformat() if account.next_run_at else None,
        last_scanned_at=account.last_scanned_at.isoformat() if account.last_scanned_at else None,
        health_status=account.health_status,
        health_error=account.health_error,
        created_at=account.created_at.isoformat() if account.created_at else "",
        latest_score_percent=latest_score,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("", response_model=CloudAccountResponse, status_code=201)
async def create_cloud_account(
    request: Request,
    body: CreateCloudAccountRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Connect a new cloud account with pre-flight role extraction and schedule."""
    prov = (body.provider or "aws").lower().strip()
    account_id = None
    role_arn = None

    if prov == "aws":
        role_arn = body.role_arn.strip() if body.role_arn else None
        if role_arn:
            arn_parts = role_arn.split(":")
            if len(arn_parts) >= 5 and arn_parts[4].isdigit():
                account_id = arn_parts[4]
    elif prov == "gcp":
        account_id = body.gcp_project_id.strip() if body.gcp_project_id else None
    elif prov == "azure":
        account_id = body.azure_subscription_id.strip() if body.azure_subscription_id else None

    next_run = _calculate_next_run(body.scan_schedule)

    account = CloudAccount(
        user_id=current_user.id,
        name=body.name.strip(),
        provider=prov,
        role_arn=role_arn,
        account_id=account_id,
        gcp_project_id=body.gcp_project_id.strip() if body.gcp_project_id else None,
        gcp_service_account_email=body.gcp_service_account_email.strip() if body.gcp_service_account_email else None,
        gcp_workload_identity_pool=body.gcp_workload_identity_pool.strip() if body.gcp_workload_identity_pool else None,
        azure_tenant_id=body.azure_tenant_id.strip() if body.azure_tenant_id else None,
        azure_subscription_id=body.azure_subscription_id.strip() if body.azure_subscription_id else None,
        azure_client_id=body.azure_client_id.strip() if body.azure_client_id else None,
        default_frameworks=body.default_frameworks,
        scan_schedule=body.scan_schedule,
        next_run_at=next_run,
        health_status="connected",  # Initialized ready
    )
    db.add(account)
    await db.flush()

    add_audit(
        db,
        user_id=current_user.id,
        action="compliance_account_added",
        request=request,
        metadata={
            "account_id": str(account.id),
            "name": account.name,
            "provider": prov,
            "cloud_account_id": account_id,
            "scan_schedule": account.scan_schedule,
        },
    )
    await db.commit()
    await db.refresh(account)

    return _serialize_account(account)


@router.get("", response_model=list[CloudAccountResponse])
async def list_cloud_accounts(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CloudAccountResponse]:
    """List all connected cloud accounts owned by the current user."""
    res = await db.execute(
        select(CloudAccount)
        .where(CloudAccount.user_id == current_user.id)
        .order_by(CloudAccount.created_at.desc())
    )
    accounts = list(res.scalars().all())

    # Fetch latest score for each account
    items: list[CloudAccountResponse] = []
    for acc in accounts:
        latest_audit = await db.execute(
            select(AuditJob)
            .where(AuditJob.cloud_account_id == acc.id, AuditJob.status == "complete")
            .order_by(AuditJob.created_at.desc())
            .limit(1)
        )
        job = latest_audit.scalar_one_or_none()
        score = None
        if job:
            snap_res = await db.execute(
                select(func.avg(ComplianceSnapshot.score_percent))
                .where(ComplianceSnapshot.audit_job_id == job.id)
            )
            raw_avg = snap_res.scalar_one_or_none()
            if raw_avg is not None:
                score = round(float(raw_avg), 2)
        items.append(_serialize_account(acc, score))

    return items


@router.get("/{account_id}", response_model=CloudAccountResponse)
async def get_cloud_account(
    account_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Retrieve details for a specific cloud account."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    res = await db.execute(
        select(CloudAccount).where(CloudAccount.id == acc_uuid, CloudAccount.user_id == current_user.id)
    )
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    # Fetch latest audit score
    latest_audit = await db.execute(
        select(AuditJob)
        .where(AuditJob.cloud_account_id == account.id, AuditJob.status == "complete")
        .order_by(AuditJob.created_at.desc())
        .limit(1)
    )
    job = latest_audit.scalar_one_or_none()
    score = None
    if job:
        snap_res = await db.execute(
            select(func.avg(ComplianceSnapshot.score_percent))
            .where(ComplianceSnapshot.audit_job_id == job.id)
        )
        raw_avg = snap_res.scalar_one_or_none()
        if raw_avg is not None:
            score = round(float(raw_avg), 2)

    return _serialize_account(account, score)


@router.patch("/{account_id}", response_model=CloudAccountResponse)
async def update_cloud_account(
    request: Request,
    account_id: str,
    body: UpdateCloudAccountRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Update settings (name, default frameworks, scan schedule) for a cloud account."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    res = await db.execute(
        select(CloudAccount).where(CloudAccount.id == acc_uuid, CloudAccount.user_id == current_user.id)
    )
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    if body.name is not None:
        account.name = body.name.strip()
    if body.default_frameworks is not None:
        account.default_frameworks = body.default_frameworks
    if body.scan_schedule is not None and body.scan_schedule != account.scan_schedule:
        account.scan_schedule = body.scan_schedule
        account.next_run_at = _calculate_next_run(body.scan_schedule)
    if body.role_arn is not None:
        account.role_arn = body.role_arn.strip()
    if body.gcp_project_id is not None:
        account.gcp_project_id = body.gcp_project_id.strip()
    if body.gcp_service_account_email is not None:
        account.gcp_service_account_email = body.gcp_service_account_email.strip()
    if body.gcp_workload_identity_pool is not None:
        account.gcp_workload_identity_pool = body.gcp_workload_identity_pool.strip()
    if body.azure_tenant_id is not None:
        account.azure_tenant_id = body.azure_tenant_id.strip()
    if body.azure_subscription_id is not None:
        account.azure_subscription_id = body.azure_subscription_id.strip()
    if body.azure_client_id is not None:
        account.azure_client_id = body.azure_client_id.strip()

    account.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(account)

    add_audit(
        db,
        user_id=current_user.id,
        action="compliance_account_updated",
        request=request,
        metadata={"account_id": str(account.id), "name": account.name},
    )
    await db.commit()

    return _serialize_account(account)


@router.delete("/{account_id}", status_code=204, response_model=None)
async def delete_cloud_account(
    request: Request,
    account_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a cloud account (preserves historical audits with cloud_account_id set to null)."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    res = await db.execute(
        select(CloudAccount).where(CloudAccount.id == acc_uuid, CloudAccount.user_id == current_user.id)
    )
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    await db.delete(account)
    add_audit(
        db,
        user_id=current_user.id,
        action="compliance_account_deleted",
        request=request,
        metadata={"account_id": account_id, "name": account.name},
    )
    await db.commit()


@router.post("/{account_id}/verify", response_model=CloudAccountResponse)
async def verify_cloud_account_connection(
    account_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Perform pre-flight verification on the cloud account's credentials across AWS, GCP, and Azure."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    res = await db.execute(
        select(CloudAccount).where(CloudAccount.id == acc_uuid, CloudAccount.user_id == current_user.id)
    )
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    prov = (account.provider or "aws").lower().strip()
    if prov == "aws":
        if not account.role_arn:
            account.health_status = "error"
            account.health_error = "Missing AWS role ARN"
        else:
            account.health_status = "connected"
            account.health_error = None
    elif prov == "gcp":
        if not account.gcp_project_id or not account.gcp_service_account_email:
            account.health_status = "error"
            account.health_error = "Missing GCP project ID or service account email"
        else:
            account.health_status = "connected"
            account.health_error = None
    elif prov == "azure":
        if not account.azure_tenant_id or not account.azure_subscription_id or not account.azure_client_id:
            account.health_status = "error"
            account.health_error = "Missing Azure tenant ID, subscription ID, or client ID"
        else:
            account.health_status = "connected"
            account.health_error = None

    account.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return _serialize_account(account)


@router.post("/{account_id}/scan", status_code=201)
async def trigger_account_scan(
    request: Request,
    account_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """1-Click Scan: Trigger an immediate compliance audit for this cloud account."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    res = await db.execute(
        select(CloudAccount).where(CloudAccount.id == acc_uuid, CloudAccount.user_id == current_user.id)
    )
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    today = date.today()
    start_date = today - timedelta(days=90)

    role_arn_val = account.role_arn or f"{account.provider}:{account.account_id or 'cloud'}"

    audit_job = AuditJob(
        user_id=current_user.id,
        cloud_account_id=account.id,
        company_name=account.name,
        role_arn=role_arn_val,
        audit_start_date=start_date,
        audit_end_date=today,
        frameworks=account.default_frameworks or ["soc2"],
        recurrence=account.scan_schedule,
        status="pending",
    )
    db.add(audit_job)
    await db.flush()

    account.last_scanned_at = datetime.now(timezone.utc)

    add_audit(
        db,
        user_id=current_user.id,
        action="compliance_audit_started",
        request=request,
        metadata={
            "audit_id": str(audit_job.id),
            "cloud_account_id": str(account.id),
            "frameworks": audit_job.frameworks,
        },
    )
    await db.commit()
    await db.refresh(audit_job)

    # Dispatch audit execution
    try:
        from app.config import settings
        from app.tasks.dev_worker import ensure_dev_worker_running

        if settings.USE_ASYNCIO_INVESTIGATION_PIPELINE and not ensure_dev_worker_running():
            from app.compliance.tasks import run_compliance_audit_inline
            asyncio.create_task(run_compliance_audit_inline(str(audit_job.id)))
        else:
            if not ensure_dev_worker_running():
                raise RuntimeError("Celery worker is unavailable")
            from app.compliance.tasks import run_soc2_audit
            run_soc2_audit.apply_async(args=[str(audit_job.id)], task_id=str(audit_job.id))
    except Exception as exc:
        logger.exception("Failed to dispatch compliance scan for account %s", account.id)
        audit_job.status = "failed"
        audit_job.error_message = "Scan could not be dispatched."
        await db.commit()
        raise HTTPException(status_code=503, detail="Scan could not be dispatched.") from exc

    return {
        "audit_id": str(audit_job.id),
        "cloud_account_id": str(account.id),
        "status": "pending",
        "message": f"Compliance audit started for '{account.name}'.",
    }

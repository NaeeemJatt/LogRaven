# LogRaven — Cloud Asset Inventory FastAPI Router
#
# PURPOSE:
#   Provides paginated inventory browsing, dynamic filters (Cloud, Service, Region, Status),
#   full-text search, executive KPI summaries, detail inspection, and on-demand discovery sync.

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.asset import CspmAsset
from app.models.soc2_audit import CloudAccount
from app.models.user import User
from app.schemas.asset import (
    AssetDetailResponse,
    AssetFiltersResponse,
    AssetListResponse,
    AssetResponse,
    AssetSummaryResponse,
    AssetSyncRequest,
    AssetSyncResponse,
    FilterItem,
)
from app.services.asset_discovery import discover_and_persist_assets
from app.utils.cookies import ACCESS_COOKIE
from app.utils.logger import get_logger
from app.utils.security import decode_token

logger = get_logger("lograven.api.assets")

router = APIRouter()


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Resolves authenticated user from lr_access cookie or Authorization Bearer header without raising 401."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token:
        return None
    try:
        payload = decode_token(token)
        uid_str = payload.get("sub")
        if not uid_str:
            return None
        uid = uuid.UUID(uid_str)
        res = await db.execute(select(User).where(User.id == uid))
        return res.scalar_one_or_none()
    except Exception as exc:
        logger.debug("Optional user resolution bypassed: %s", exc)
        return None


SERVICE_LABELS: Dict[str, str] = {
    "EC2": "EC2 (Virtual Machines)",
    "SECURITY_GROUP": "Security Groups",
    "LOAD_BALANCER": "Load Balancers",
    "API_GATEWAY": "API Gateway",
    "LOG_GROUP": "CloudWatch Log Groups",
    "LAMBDA": "Lambda Functions",
    "IAM": "IAM",
    "S3": "S3",
    "RDS": "RDS",
    "KINESIS": "Kinesis Streams",
    "EKS": "EKS (Kubernetes)",
    "ECS": "ECS (Containers & Tasks)",
    "ECR": "ECR (Container Registry)",
    "DYNAMODB": "DynamoDB Tables",
    "ELASTICACHE": "ElastiCache Clusters",
    "SECRETS_MANAGER": "Secrets Manager",
    "ACM": "ACM Certificates",
    "WAF": "WAF Web ACLs",
    "CLOUD_FRONT": "CloudFront Distributions",
    "ROUTE_53": "Route 53 DNS",
    "SQS": "SQS Queues",
    "SNS": "SNS Topics",
    "KMS": "KMS",
    "CLOUD_TRAIL": "CloudTrail",
    "VPC": "VPC & Subnets",
}


@router.get("", response_model=AssetListResponse, summary="List & Filter Cloud Assets")
async def list_assets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    search: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetListResponse:
    """
    Returns a paginated list of cloud assets with multi-attribute filtering
    across Cloud Provider, Service, Region, and Compliance Status.
    """
    user_id = current_user.id if current_user else None

    # Check if inventory has any records; if completely empty, run baseline sync
    count_check = await db.execute(select(func.count(CspmAsset.urn)))
    if (count_check.scalar() or 0) == 0:
        logger.info("Asset inventory is empty; seeding initial cloud inventory...")
        await discover_and_persist_assets(db, user_id=user_id)

    q = select(CspmAsset).where(CspmAsset.is_deleted == False)

    # Multi-tenant scoping: if user is authenticated, scope to user's accounts and tenant
    if current_user:
        user_acc_q = select(CloudAccount.id).where(CloudAccount.user_id == current_user.id)
        q = q.where(
            or_(
                CspmAsset.tenant_id == current_user.id,
                CspmAsset.cloud_account_id.in_(user_acc_q),
            )
        )

    # 1. Text search across name, id, URN
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                CspmAsset.resource_name.ilike(term),
                CspmAsset.resource_id.ilike(term),
                CspmAsset.urn.ilike(term),
                CspmAsset.service.ilike(term),
            )
        )

    # 2. Filters
    if provider and provider.lower() != "all":
        q = q.where(func.lower(CspmAsset.provider) == provider.lower())

    if service and service.lower() != "all":
        q = q.where(func.lower(CspmAsset.service) == service.lower())

    if region and region.lower() != "all":
        q = q.where(func.lower(CspmAsset.region) == region.lower())

    if status and status.lower() != "all":
        q = q.where(func.lower(CspmAsset.compliance_status) == status.lower())

    if account_id and account_id.lower() != "all":
        q = q.where(CspmAsset.account_id == account_id)

    # Count total matching query
    count_q = select(func.count()).select_from(q.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    # Paginate and order by last_seen_at desc
    offset = (page - 1) * limit
    q = q.order_by(CspmAsset.last_seen_at.desc(), CspmAsset.resource_name.asc()).offset(offset).limit(limit)
    res = await db.execute(q)
    assets = list(res.scalars().all())

    total_pages = max(1, math.ceil(total / limit))

    return AssetListResponse(
        items=[AssetResponse.model_validate(a) for a in assets],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/filters", response_model=AssetFiltersResponse, summary="Get Filter Options & Counts")
async def get_asset_filters(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetFiltersResponse:
    """
    Returns distinct available Cloud Providers, Services, Regions, and Statuses
    with real-time resource counts for UI dropdown filters.
    """
    base_where = [CspmAsset.is_deleted == False]
    if current_user:
        user_acc_q = select(CloudAccount.id).where(CloudAccount.user_id == current_user.id)
        base_where.append(
            or_(
                CspmAsset.tenant_id == current_user.id,
                CspmAsset.cloud_account_id.in_(user_acc_q),
            )
        )

    # Providers
    p_res = await db.execute(
        select(CspmAsset.provider, func.count(CspmAsset.urn))
        .where(*base_where)
        .group_by(CspmAsset.provider)
        .order_by(func.count(CspmAsset.urn).desc())
    )
    providers = [FilterItem(value=row[0], count=row[1], label=row[0].upper()) for row in p_res.all()]

    # Services
    s_res = await db.execute(
        select(CspmAsset.service, func.count(CspmAsset.urn))
        .where(*base_where)
        .group_by(CspmAsset.service)
        .order_by(func.count(CspmAsset.urn).desc())
    )
    services = [
        FilterItem(
            value=row[0],
            count=row[1],
            label=SERVICE_LABELS.get(str(row[0]).upper(), str(row[0]).replace("_", " ").title()),
        )
        for row in s_res.all()
    ]

    # Regions
    r_res = await db.execute(
        select(CspmAsset.region, func.count(CspmAsset.urn))
        .where(*base_where)
        .group_by(CspmAsset.region)
        .order_by(func.count(CspmAsset.urn).desc())
    )
    regions = [FilterItem(value=row[0], count=row[1], label=row[0]) for row in r_res.all()]

    # Statuses
    st_res = await db.execute(
        select(CspmAsset.compliance_status, func.count(CspmAsset.urn))
        .where(*base_where)
        .group_by(CspmAsset.compliance_status)
        .order_by(func.count(CspmAsset.urn).desc())
    )
    statuses = [FilterItem(value=row[0], count=row[1], label=row[0].replace("_", " ").title()) for row in st_res.all()]

    return AssetFiltersResponse(
        providers=providers,
        services=services,
        regions=regions,
        statuses=statuses,
    )


@router.get("/summary", response_model=AssetSummaryResponse, summary="Get Asset Inventory Summary Metrics")
async def get_asset_summary(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetSummaryResponse:
    """Returns top KPI summary metrics for the Asset Inventory header."""
    q = select(
        func.count(CspmAsset.urn).label("total"),
        func.count(case((CspmAsset.compliance_status == "COMPLIANT", 1))).label("compliant"),
        func.count(case((CspmAsset.compliance_status == "NON_COMPLIANT", 1))).label("non_compliant"),
        func.count(case((CspmAsset.compliance_status == "UNASSESSED", 1))).label("unassessed"),
        func.count(distinct(CspmAsset.service)).label("services_count"),
        func.count(distinct(CspmAsset.account_id)).label("accounts_count"),
    ).where(CspmAsset.is_deleted == False)

    if current_user:
        user_acc_q = select(CloudAccount.id).where(CloudAccount.user_id == current_user.id)
        q = q.where(
            or_(
                CspmAsset.tenant_id == current_user.id,
                CspmAsset.cloud_account_id.in_(user_acc_q),
            )
        )

    res = await db.execute(q)
    row = res.one()

    return AssetSummaryResponse(
        total_assets=row.total or 0,
        compliant_assets=row.compliant or 0,
        non_compliant_assets=row.non_compliant or 0,
        unassessed_assets=row.unassessed or 0,
        services_count=row.services_count or 0,
        accounts_count=row.accounts_count or 0,
    )


@router.get("/{urn:path}", response_model=AssetDetailResponse, summary="Get Asset Details by URN")
async def get_asset_detail(
    urn: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetDetailResponse:
    """Returns the complete asset record including full JSON configuration and tags."""
    q = select(CspmAsset).where(CspmAsset.urn == urn, CspmAsset.is_deleted == False)
    res = await db.execute(q)
    asset = res.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset not found: {urn}")

    return AssetDetailResponse.model_validate(asset)


@router.post("/sync", response_model=AssetSyncResponse, summary="Trigger Cloud Asset Discovery Sync")
async def sync_assets_endpoint(
    body: Optional[AssetSyncRequest] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetSyncResponse:
    """Triggers live Boto3 cloud asset discovery and updates cspm_assets."""
    user_id = current_user.id if current_user else None
    c_acc_id = body.cloud_account_id if body else None

    result = await discover_and_persist_assets(db, cloud_account_id=c_acc_id, user_id=user_id)

    return AssetSyncResponse(
        status="success",
        synced_assets_count=result.get("synced_assets_count", 0),
        services=result.get("services", []),
        message="Cloud asset discovery completed successfully.",
        synced_at=result.get("synced_at", ""),
    )

"""FastAPI Router & Crawler Engine for Module 02: Cross-Cloud Asset Discovery & CAASM."""

import uuid
from typing import Any, Dict, List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod02_asset_crawler.internal.repository.asset_repo import AssetRepository
from services.mod02_asset_crawler.internal.repository.models import CSPMAsset
from services.mod02_asset_crawler.internal.normalizer.urn_builder import parse_urn
from services.mod02_asset_crawler.internal.publisher.kafka_publisher import AssetEventPublisher
from services.mod02_asset_crawler.internal.collectors.aws_bulk_collector import AWSBulkCollector

router = APIRouter(prefix="/assets", tags=["asset-inventory-caasm"])

_publisher = AssetEventPublisher()
_collector = AWSBulkCollector()


# ── Schemas ──────────────────────────────────────────────────────────────

class AssetDetailResponse(BaseModel):
    urn: str
    tenant_id: uuid.UUID
    account_id: str
    provider: str
    region: str
    service: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    config_json: Dict[str, Any]
    config_sha256: str
    is_deleted: bool
    first_seen_at: Any
    last_seen_at: Any


class CrawlAccountRequest(BaseModel):
    account_id: str = Field(..., description="Cloud Account identifier")
    provider: str = Field(default="aws")
    regions: Optional[List[str]] = Field(default_factory=lambda: ["us-east-1"])


class CrawlSummaryResponse(BaseModel):
    account_id: str
    provider: str
    total_discovered: int
    mutated_assets: int
    tombstoned_assets: int
    active_assets: int


# ── Crawler Service Pipeline ─────────────────────────────────────────────

async def process_account_crawl(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: str,
    provider: str,
    discovered_raw_assets: List[Dict[str, Any]],
    publisher: Optional[AssetEventPublisher] = None,
) -> Dict[str, Any]:
    """Upserts crawled assets, emits delta events to topic cspm.asset.mutated, and tombstones deleted resources."""
    pub = publisher or _publisher
    active_urns: Set[str] = set()
    mutated_count = 0

    for asset_dict in discovered_raw_assets:
        urn = asset_dict["urn"]
        active_urns.add(urn)

        asset, is_new, is_mutated, old_sha = await AssetRepository.upsert_asset(
            session=session,
            urn=urn,
            tenant_id=tenant_id,
            account_id=account_id,
            provider=provider,
            region=asset_dict["region"],
            service=asset_dict["service"],
            resource_type=asset_dict["resource_type"],
            resource_id=asset_dict["resource_id"],
            config_dict=asset_dict["config"],
            resource_name=asset_dict.get("resource_name"),
        )

        if is_mutated:
            mutated_count += 1
            change_type = "CREATED" if is_new else "CONFIG_DRIFT"
            await pub.emit_mutation(
                tenant_id=str(tenant_id),
                urn=urn,
                change_type=change_type,
                current_sha256=asset.config_sha256,
                previous_sha256=old_sha,
            )

    # Tombstone any unobserved resources (FR-MOD2-05, TC-MOD2-005)
    tombstoned = await AssetRepository.tombstone_missing_assets(
        session=session,
        tenant_id=tenant_id,
        account_id=account_id,
        provider=provider,
        active_urns=active_urns,
    )

    for dead_asset in tombstoned:
        await pub.emit_mutation(
            tenant_id=str(tenant_id),
            urn=dead_asset.urn,
            change_type="DELETED",
            current_sha256=dead_asset.config_sha256,
            previous_sha256=dead_asset.config_sha256,
        )

    await session.commit()

    return {
        "account_id": account_id,
        "provider": provider,
        "total_discovered": len(discovered_raw_assets),
        "mutated_assets": mutated_count,
        "tombstoned_assets": len(tombstoned),
        "active_assets": len(active_urns),
    }


# ── REST API Endpoints ───────────────────────────────────────────────────

@router.get("", response_model=List[AssetDetailResponse])
async def list_inventory_assets(
    provider: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List normalized multi-cloud assets with filtering by provider, service, and deletion state."""
    assets = await AssetRepository.list_assets(
        session=db,
        tenant_id=current_user.id,
        provider=provider,
        service=service,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    return assets


@router.get("/{urn:path}", response_model=AssetDetailResponse)
async def get_inventory_asset(
    urn: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve deep normalized asset configuration by Canonical URN."""
    asset = await AssetRepository.get_by_urn(session=db, urn=urn, tenant_id=current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/crawl", response_model=CrawlSummaryResponse)
async def trigger_account_crawl(
    req: CrawlAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger inventory crawl and return delta sweep metrics."""
    raw_assets = await _collector.crawl_account(
        account_id=req.account_id,
        regions=req.regions,
    )
    summary = await process_account_crawl(
        session=db,
        tenant_id=current_user.id,
        account_id=req.account_id,
        provider=req.provider,
        discovered_raw_assets=raw_assets,
    )
    return summary


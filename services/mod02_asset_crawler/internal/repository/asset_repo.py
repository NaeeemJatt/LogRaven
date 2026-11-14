"""Persistence repository for Normalized CSPM Assets and Delta Detection."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod02_asset_crawler.internal.repository.models import CSPMAsset
from services.mod02_asset_crawler.internal.normalizer.canonical_hasher import canonicalize_config


class AssetRepository:
    """Async repository managing CSPM assets with delta detection and soft-delete tombstoning."""

    @staticmethod
    async def upsert_asset(
        session: AsyncSession,
        urn: str,
        tenant_id: uuid.UUID,
        account_id: str,
        provider: str,
        region: str,
        service: str,
        resource_type: str,
        resource_id: str,
        config_dict: Dict[str, Any],
        resource_name: Optional[str] = None,
    ) -> Tuple[CSPMAsset, bool, bool, Optional[str]]:
        """Upsert asset and compute configuration delta.
        
        Returns:
            Tuple of (asset, is_new, is_mutated, previous_sha256)
        """
        cleaned_config, new_sha256 = canonicalize_config(config_dict)
        now = datetime.now(timezone.utc)

        # Check existing asset
        query = select(CSPMAsset).where(CSPMAsset.urn == urn)
        result = await session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            old_sha = existing.config_sha256
            existing.last_seen_at = now
            is_mutated = False

            # Check for config drift or un-deletion
            if existing.is_deleted or old_sha != new_sha256:
                existing.config_json = cleaned_config
                existing.config_sha256 = new_sha256
                existing.is_deleted = False
                existing.deleted_at = None
                if resource_name:
                    existing.resource_name = resource_name
                is_mutated = True

            await session.flush()
            return existing, False, is_mutated, old_sha
        else:
            # Create new asset
            new_asset = CSPMAsset(
                urn=urn,
                tenant_id=tenant_id,
                account_id=account_id,
                provider=provider.lower().strip(),
                region=region.lower().strip(),
                service=service.lower().strip(),
                resource_type=resource_type.lower().strip(),
                resource_id=resource_id.strip(),
                resource_name=resource_name or resource_id,
                config_json=cleaned_config,
                config_sha256=new_sha256,
                is_deleted=False,
                first_seen_at=now,
                last_seen_at=now,
                deleted_at=None,
            )
            session.add(new_asset)
            await session.flush()
            return new_asset, True, True, None

    @staticmethod
    async def tombstone_missing_assets(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        account_id: str,
        provider: str,
        active_urns: Set[str],
    ) -> List[CSPMAsset]:
        """Marks any currently active assets missing from active_urns as soft-deleted (tombstoned).
        
        Returns list of newly tombstoned CSPMAsset entities (FR-MOD2-05, TC-MOD2-005).
        """
        now = datetime.now(timezone.utc)
        query = select(CSPMAsset).where(
            CSPMAsset.tenant_id == tenant_id,
            CSPMAsset.account_id == str(account_id).strip(),
            CSPMAsset.provider == provider.lower().strip(),
            CSPMAsset.is_deleted == False,
        )
        result = await session.execute(query)
        all_active = result.scalars().all()

        tombstoned = []
        for asset in all_active:
            if asset.urn not in active_urns:
                asset.is_deleted = True
                asset.deleted_at = now
                tombstoned.append(asset)

        if tombstoned:
            await session.flush()

        return tombstoned

    @staticmethod
    async def get_by_urn(
        session: AsyncSession,
        urn: str,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[CSPMAsset]:
        """Fetch asset by URN with optional tenant scoping."""
        query = select(CSPMAsset).where(CSPMAsset.urn == urn)
        if tenant_id:
            query = query.where(CSPMAsset.tenant_id == tenant_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_assets(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider: Optional[str] = None,
        service: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CSPMAsset]:
        """List assets for tenant with filtering."""
        query = select(CSPMAsset).where(CSPMAsset.tenant_id == tenant_id)
        if not include_deleted:
            query = query.where(CSPMAsset.is_deleted == False)
        if provider:
            query = query.where(CSPMAsset.provider == provider.lower().strip())
        if service:
            query = query.where(CSPMAsset.service == service.lower().strip())
        query = query.order_by(CSPMAsset.last_seen_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())


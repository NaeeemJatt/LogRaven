"""Repository for DSPM Data Assets and Sensitive Data Classifications (PRD-MOD-08)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod08_dspm_classifier.internal.repository.models import (
    DSPMClassification,
    DSPMDataAsset,
)


class DSPMRepository:
    """Persistence operations for DSPM assets and zero-exfiltration classifications."""

    @staticmethod
    async def record_data_asset_scan(
        session: AsyncSession,
        asset_urn: str,
        storage_type: str,
        total_objects_count: int,
        sampled_objects_count: int,
        contains_pii: bool,
        contains_pci: bool,
        contains_phi: bool,
        contains_secrets: bool,
        encryption_type: str,
        is_ransomware_vulnerable: bool,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> DSPMDataAsset:
        """Upserts a scanned data asset posture record."""
        now = datetime.now(timezone.utc)
        query = select(DSPMDataAsset).where(DSPMDataAsset.asset_urn == asset_urn)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.storage_type = storage_type
            existing.total_objects_count = total_objects_count
            existing.sampled_objects_count = sampled_objects_count
            existing.contains_pii = contains_pii
            existing.contains_pci = contains_pci
            existing.contains_phi = contains_phi
            existing.contains_secrets = contains_secrets
            existing.encryption_type = encryption_type
            existing.is_ransomware_vulnerable = is_ransomware_vulnerable
            existing.scanned_at = now
            await session.flush()
            return existing
        else:
            asset = DSPMDataAsset(
                tenant_id=tenant_id,
                asset_urn=asset_urn,
                storage_type=storage_type,
                total_objects_count=total_objects_count,
                sampled_objects_count=sampled_objects_count,
                contains_pii=contains_pii,
                contains_pci=contains_pci,
                contains_phi=contains_phi,
                contains_secrets=contains_secrets,
                encryption_type=encryption_type,
                is_ransomware_vulnerable=is_ransomware_vulnerable,
                scanned_at=now,
            )
            session.add(asset)
            await session.flush()
            return asset

    @staticmethod
    async def record_classification(
        session: AsyncSession,
        data_asset_id: uuid.UUID,
        category: str,
        detector_name: str,
        confidence: str = "HIGH",
        match_count: int = 1,
        file_extension: str = "",
        byte_offset: Optional[int] = None,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> DSPMClassification:
        """Stores a sensitive data finding with zero raw payload exfiltration (NFR-MOD8-01)."""
        classification = DSPMClassification(
            data_asset_id=data_asset_id,
            tenant_id=tenant_id,
            category=category,
            detector_name=detector_name,
            confidence=confidence,
            match_count=match_count,
            file_extension=file_extension,
            byte_offset=byte_offset,
        )
        session.add(classification)
        await session.flush()
        return classification

    @staticmethod
    async def get_asset_by_urn(
        session: AsyncSession,
        asset_urn: str,
    ) -> Optional[DSPMDataAsset]:
        """Retrieves asset record by URN."""
        query = select(DSPMDataAsset).where(DSPMDataAsset.asset_urn == asset_urn)
        res = await session.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_assets(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DSPMDataAsset]:
        """Lists scanned data assets."""
        query = select(DSPMDataAsset).order_by(desc(DSPMDataAsset.scanned_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def list_classifications_for_asset(
        session: AsyncSession,
        data_asset_id: uuid.UUID,
    ) -> List[DSPMClassification]:
        """Lists classification matches for a data asset."""
        query = select(DSPMClassification).where(DSPMClassification.data_asset_id == data_asset_id)
        res = await session.execute(query)
        return list(res.scalars().all())

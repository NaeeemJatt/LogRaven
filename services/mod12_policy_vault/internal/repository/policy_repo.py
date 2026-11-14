"""Repository for Module 12: Visual-to-Rego Studio & Audit Vault (PRD-MOD-12)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod12_policy_vault.internal.repository.models import (
    CrowdstrikeSuppressionRule,
    CustomRegoRule,
    VaultPackage,
)


class PolicyVaultRepository:
    """Persistence operations for Custom Rego Rules, CrowdStrike Suppressions, and Vault Packages."""

    @staticmethod
    async def create_custom_rule(
        session: AsyncSession,
        rule_id: str,
        name: str,
        resource_type: str,
        visual_ast: Dict[str, Any],
        rego_code: str,
        description: Optional[str] = None,
        severity: str = "HIGH",
        tenant_id: Optional[uuid.UUID] = None,
    ) -> CustomRegoRule:
        """Upserts a custom visual/Rego rule."""
        query = select(CustomRegoRule).where(CustomRegoRule.rule_id == rule_id)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.name = name
            existing.description = description
            existing.severity = severity
            existing.resource_type = resource_type
            existing.visual_ast = visual_ast
            existing.rego_code = rego_code
            existing.is_active = True
            await session.flush()
            return existing
        else:
            record = CustomRegoRule(
                tenant_id=tenant_id,
                rule_id=rule_id,
                name=name,
                description=description,
                severity=severity,
                resource_type=resource_type,
                visual_ast=visual_ast,
                rego_code=rego_code,
                is_active=True,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def create_suppression_rule(
        session: AsyncSession,
        name: str,
        justification: str,
        approver: str,
        finding_type: Optional[str] = None,
        account_ids: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        tag_filters: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> CrowdstrikeSuppressionRule:
        """Creates a scoped suppression rule."""
        record = CrowdstrikeSuppressionRule(
            tenant_id=tenant_id,
            name=name,
            finding_type=finding_type,
            account_ids=account_ids or [],
            regions=regions or [],
            tag_filters=tag_filters or {},
            justification=justification,
            approver=approver,
            status="ACTIVE",
            expires_at=expires_at,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def list_active_suppressions(session: AsyncSession) -> List[CrowdstrikeSuppressionRule]:
        """Lists active suppression rules."""
        query = select(CrowdstrikeSuppressionRule).where(CrowdstrikeSuppressionRule.status == "ACTIVE")
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def sweep_expired_suppressions(session: AsyncSession) -> int:
        """Transitions any active suppression rule where now() > expires_at to 'EXPIRED' status."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(CrowdstrikeSuppressionRule)
            .where(
                CrowdstrikeSuppressionRule.status == "ACTIVE",
                CrowdstrikeSuppressionRule.expires_at.isnot(None),
                CrowdstrikeSuppressionRule.expires_at < now,
            )
            .values(status="EXPIRED")
        )
        res = await session.execute(stmt)
        await session.flush()
        return res.rowcount

    @staticmethod
    async def record_vault_package(
        session: AsyncSession,
        package_name: str,
        merkle_root_hash: str,
        file_hashes: Dict[str, str],
        package_path: Optional[str] = None,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> VaultPackage:
        """Records a cryptographically sealed evidence vault package."""
        record = VaultPackage(
            tenant_id=tenant_id,
            package_name=package_name,
            merkle_root_hash=merkle_root_hash,
            file_hashes=file_hashes,
            package_path=package_path,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def list_custom_rules(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CustomRegoRule]:
        query = select(CustomRegoRule).order_by(desc(CustomRegoRule.created_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())

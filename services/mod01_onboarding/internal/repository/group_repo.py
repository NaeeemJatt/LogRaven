"""Group repository layer for CloudGroup."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod01_onboarding.internal.repository.models import CloudGroup


class GroupRepository:
    """Async repository for CloudGroup CRUD."""

    @staticmethod
    async def create_group(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        business_impact: str,
        environment: str,
        account_ids: Optional[List[uuid.UUID]] = None,
        tag_filters: Optional[Dict[str, Any]] = None,
    ) -> CloudGroup:
        """Create cloud group."""
        impact = business_impact.lower().strip()
        env = environment.lower().strip()
        if impact not in ("critical", "high", "medium", "low"):
            raise ValueError(f"Invalid business_impact: {business_impact}")
        if env not in ("prod", "staging", "dev"):
            raise ValueError(f"Invalid environment: {environment}")

        group = CloudGroup(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name.strip(),
            business_impact=impact,
            environment=env,
            account_ids=[str(a) for a in (account_ids or [])],
            tag_filters=tag_filters or {},
        )
        session.add(group)
        await session.flush()
        return group

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        group_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[CloudGroup]:
        """Fetch group by ID with optional tenant scope enforcement."""
        query = select(CloudGroup).where(CloudGroup.id == group_id)
        if tenant_id:
            query = query.where(CloudGroup.tenant_id == tenant_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_groups(
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> List[CloudGroup]:
        """List cloud groups for tenant."""
        query = select(CloudGroup).where(CloudGroup.tenant_id == tenant_id).order_by(CloudGroup.name.asc())
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def add_account_to_group(
        session: AsyncSession,
        group_id: uuid.UUID,
        account_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[CloudGroup]:
        """Add cloud account ID to group account_ids list."""
        group = await GroupRepository.get_by_id(session, group_id, tenant_id=tenant_id)
        if not group:
            return None
        acct_str = str(account_id)
        if acct_str not in group.account_ids:
            group.account_ids = group.account_ids + [acct_str]
            group.updated_at = datetime.now(timezone.utc)
            await session.flush()
        return group


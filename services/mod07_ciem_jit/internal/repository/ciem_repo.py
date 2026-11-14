"""Repository for CIEM Entitlements and ChatOps JIT Leases (PRD-MOD-07)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod07_ciem_jit.internal.repository.models import CloudEntitlement, CloudJITLease


class CIEMRepository:
    """Persistence operations for Cloud Entitlements and JIT Leases."""

    @staticmethod
    async def upsert_entitlement(
        session: AsyncSession,
        principal_arn: str,
        provider: str,
        granted_actions: List[str],
        used_actions_90d: List[str],
        is_admin: bool,
        has_toxic_combinations: bool,
        toxic_vectors: List[str],
        tenant_id: Optional[uuid.UUID] = None,
    ) -> CloudEntitlement:
        """Upserts calculated entitlement analysis for an IAM principal."""
        now = datetime.now(timezone.utc)
        unused_count = max(0, len(granted_actions) - len(used_actions_90d))

        query = select(CloudEntitlement).where(CloudEntitlement.principal_arn == principal_arn)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.provider = provider
            existing.granted_actions = granted_actions
            existing.used_actions_90d = used_actions_90d
            existing.unused_actions_count = unused_count
            existing.is_admin = is_admin
            existing.has_toxic_combinations = has_toxic_combinations
            existing.toxic_vectors = toxic_vectors
            existing.last_evaluated_at = now
            await session.flush()
            return existing
        else:
            record = CloudEntitlement(
                tenant_id=tenant_id,
                principal_arn=principal_arn,
                provider=provider,
                granted_actions=granted_actions,
                used_actions_90d=used_actions_90d,
                unused_actions_count=unused_count,
                is_admin=is_admin,
                has_toxic_combinations=has_toxic_combinations,
                toxic_vectors=toxic_vectors,
                last_evaluated_at=now,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def get_entitlement(
        session: AsyncSession,
        principal_arn: str,
    ) -> Optional[CloudEntitlement]:
        """Retrieves entitlement details for a principal."""
        query = select(CloudEntitlement).where(CloudEntitlement.principal_arn == principal_arn)
        res = await session.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_jit_lease(
        session: AsyncSession,
        requester_email: str,
        target_role_arn: str,
        justification: str,
        duration_minutes: int,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> CloudJITLease:
        """Creates a pending JIT lease request."""
        lease = CloudJITLease(
            tenant_id=tenant_id,
            requester_email=requester_email,
            target_role_arn=target_role_arn,
            justification=justification,
            duration_minutes=duration_minutes,
            status="REQUESTED",
        )
        session.add(lease)
        await session.flush()
        return lease

    @staticmethod
    async def get_jit_lease(
        session: AsyncSession,
        lease_id: uuid.UUID,
    ) -> Optional[CloudJITLease]:
        """Retrieves a JIT lease by ID."""
        query = select(CloudJITLease).where(CloudJITLease.id == lease_id)
        res = await session.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_expiring_or_expired_leases(
        session: AsyncSession,
        now: Optional[datetime] = None,
    ) -> List[CloudJITLease]:
        """Finds active leases whose expires_at is past the current time."""
        curr_time = now or datetime.now(timezone.utc)
        query = select(CloudJITLease).where(
            CloudJITLease.status.in_(["ACTIVE", "APPROVED"]),
            CloudJITLease.expires_at <= curr_time,
        )
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def list_leases(
        session: AsyncSession,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CloudJITLease]:
        """Lists JIT leases with optional status filter."""
        query = select(CloudJITLease)
        if status_filter:
            query = query.where(CloudJITLease.status == status_filter)
        query = query.order_by(desc(CloudJITLease.created_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())

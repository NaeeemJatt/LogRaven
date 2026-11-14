"""Repository for Module 10: KSPM & Kubernetes Admission Controller (PRD-MOD-10)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod10_kspm_kac.internal.repository.models import K8sAdmissionEvent, K8sCluster


class KSPMRepository:
    """Persistence operations for Kubernetes clusters and admission review events."""

    @staticmethod
    async def upsert_cluster(
        session: AsyncSession,
        asset_urn: str,
        cluster_name: str,
        distribution: str = "EKS",
        k8s_version: str = "v1.30.0",
        kac_webhook_installed: bool = True,
        kac_enforcement_mode: str = "AUDIT",
        namespaces_count: int = 0,
        pods_count: int = 0,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> K8sCluster:
        """Upserts a Kubernetes cluster inventory record."""
        now = datetime.now(timezone.utc)
        query = select(K8sCluster).where(K8sCluster.asset_urn == asset_urn)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.cluster_name = cluster_name
            existing.distribution = distribution
            existing.k8s_version = k8s_version
            existing.kac_webhook_installed = kac_webhook_installed
            existing.kac_enforcement_mode = kac_enforcement_mode
            existing.namespaces_count = namespaces_count
            existing.pods_count = pods_count
            existing.last_crawled_at = now
            await session.flush()
            return existing
        else:
            record = K8sCluster(
                tenant_id=tenant_id,
                asset_urn=asset_urn,
                cluster_name=cluster_name,
                distribution=distribution,
                k8s_version=k8s_version,
                kac_webhook_installed=kac_webhook_installed,
                kac_enforcement_mode=kac_enforcement_mode,
                namespaces_count=namespaces_count,
                pods_count=pods_count,
                last_crawled_at=now,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def record_admission_event(
        session: AsyncSession,
        cluster_id: uuid.UUID,
        resource_kind: str,
        resource_name: str,
        namespace: str,
        operation: str,
        allowed: bool,
        violated_policies: List[Dict[str, Any]],
        tenant_id: Optional[uuid.UUID] = None,
    ) -> K8sAdmissionEvent:
        """Records an evaluated Kubernetes admission review event."""
        now = datetime.now(timezone.utc)
        record = K8sAdmissionEvent(
            tenant_id=tenant_id,
            cluster_id=cluster_id,
            resource_kind=resource_kind,
            resource_name=resource_name,
            namespace=namespace,
            operation=operation,
            allowed=allowed,
            violated_policies=violated_policies,
            evaluated_at=now,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def list_clusters(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[K8sCluster]:
        """Lists cataloged Kubernetes clusters."""
        query = select(K8sCluster).order_by(desc(K8sCluster.last_crawled_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def list_admission_events(
        session: AsyncSession,
        cluster_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[K8sAdmissionEvent]:
        """Lists evaluated admission events."""
        query = select(K8sAdmissionEvent).order_by(desc(K8sAdmissionEvent.evaluated_at)).limit(limit).offset(offset)
        if cluster_id:
            query = query.where(K8sAdmissionEvent.cluster_id == cluster_id)
        res = await session.execute(query)
        return list(res.scalars().all())

"""Repository for Unified Security Graph, Attack Paths, and Chokepoints (PRD-MOD-06)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod06_security_graph.internal.repository.models import (
    SecurityAttackPath,
    SecurityGraphEdge,
    SecurityGraphNode,
)


class SecurityGraphRepository:
    """Async persistence repository for nodes, edges, attack paths, and chokepoints."""

    @staticmethod
    async def upsert_node(
        session: AsyncSession,
        node_id: str,
        domain: str,
        label: str,
        provider: str = "aws",
        is_internet_facing: bool = False,
        truerisk_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> SecurityGraphNode:
        """Upserts a graph node belonging to one of the 6 security domains."""
        now = datetime.now(timezone.utc)
        meta = metadata or {}

        query = select(SecurityGraphNode).where(SecurityGraphNode.id == node_id)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.domain = domain
            existing.label = label
            existing.provider = provider
            existing.is_internet_facing = is_internet_facing
            existing.truerisk_score = truerisk_score
            existing.raw_metadata = meta
            existing.updated_at = now
            await session.flush()
            return existing
        else:
            node = SecurityGraphNode(
                id=node_id,
                tenant_id=tenant_id,
                domain=domain,
                provider=provider,
                label=label,
                is_internet_facing=is_internet_facing,
                truerisk_score=truerisk_score,
                raw_metadata=meta,
                created_at=now,
                updated_at=now,
            )
            session.add(node)
            await session.flush()
            return node

    @staticmethod
    async def upsert_edge(
        session: AsyncSession,
        edge_id: str,
        source_id: str,
        target_id: str,
        relationship: str,
        remediation_friction: float = 1.0,
        is_attack_path: bool = False,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> SecurityGraphEdge:
        """Upserts a directed relationship edge between two nodes."""
        query = select(SecurityGraphEdge).where(SecurityGraphEdge.id == edge_id)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.relationship = relationship
            existing.remediation_friction = remediation_friction
            existing.is_attack_path = is_attack_path
            await session.flush()
            return existing
        else:
            edge = SecurityGraphEdge(
                id=edge_id,
                tenant_id=tenant_id,
                source_id=source_id,
                target_id=target_id,
                relationship=relationship,
                remediation_friction=remediation_friction,
                is_attack_path=is_attack_path,
            )
            session.add(edge)
            await session.flush()
            return edge

    @staticmethod
    async def record_attack_path(
        session: AsyncSession,
        title: str,
        source_node_id: str,
        target_crown_jewel_id: str,
        path_length: int,
        node_path: List[str],
        truerisk_score: float,
        chokepoint_edge_id: Optional[str] = None,
        chokepoint_description: Optional[str] = None,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> SecurityAttackPath:
        """Persists an identified attack path with its calculated TrueRisk and chokepoint."""
        record = SecurityAttackPath(
            tenant_id=tenant_id,
            title=title,
            source_node_id=source_node_id,
            target_crown_jewel_id=target_crown_jewel_id,
            path_length=path_length,
            node_path=node_path,
            truerisk_score=truerisk_score,
            chokepoint_edge_id=chokepoint_edge_id,
            chokepoint_description=chokepoint_description,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def list_attack_paths(
        session: AsyncSession,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SecurityAttackPath]:
        """Lists attack paths sorted by TrueRisk score descending."""
        query = select(SecurityAttackPath)
        if tenant_id:
            query = query.where(SecurityAttackPath.tenant_id == tenant_id)
        query = query.order_by(desc(SecurityAttackPath.truerisk_score)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def get_all_nodes(
        session: AsyncSession,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> List[SecurityGraphNode]:
        """Retrieves all graph nodes."""
        query = select(SecurityGraphNode)
        if tenant_id:
            query = query.where(SecurityGraphNode.tenant_id == tenant_id)
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def get_all_edges(
        session: AsyncSession,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> List[SecurityGraphEdge]:
        """Retrieves all graph edges."""
        query = select(SecurityGraphEdge)
        if tenant_id:
            query = query.where(SecurityGraphEdge.tenant_id == tenant_id)
        res = await session.execute(query)
        return list(res.scalars().all())

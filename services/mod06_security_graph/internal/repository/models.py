"""SQLAlchemy ORM models for Unified Security Graph & Attack Paths (PRD-MOD-06)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SecurityGraphNode(Base):
    __tablename__ = "security_graph_nodes"

    id: Mapped[str] = mapped_column(String(512), primary_key=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # COMPUTE, STORAGE, NETWORK, IDENTITY, VULNERABILITY, DATA
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="aws")  # aws, gcp, azure
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    is_internet_facing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    truerisk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SecurityGraphEdge(Base):
    __tablename__ = "security_graph_edges"

    id: Mapped[str] = mapped_column(String(512), primary_key=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(
        String(512),
        ForeignKey("security_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[str] = mapped_column(
        String(512),
        ForeignKey("security_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship: Mapped[str] = mapped_column(String(64), nullable=False)  # EXPOSES, ATTACHES_TO, ASSUMES_ROLE, etc.
    remediation_friction: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_attack_path: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SecurityAttackPath(Base):
    __tablename__ = "security_attack_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_node_id: Mapped[str] = mapped_column(
        String(512),
        ForeignKey("security_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_crown_jewel_id: Mapped[str] = mapped_column(
        String(512),
        ForeignKey("security_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path_length: Mapped[int] = mapped_column(Integer, nullable=False)
    node_path: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    truerisk_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    chokepoint_edge_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    chokepoint_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

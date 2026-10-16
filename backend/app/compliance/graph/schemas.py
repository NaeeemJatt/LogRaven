"""Pydantic schemas for Attack Path & Cloud Asset Relationship Graph."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

CategoryType = Literal[
    "internet",
    "network",
    "compute",
    "identity",
    "storage",
    "database",
    "security_service",
]

SeverityType = Literal["clean", "low", "medium", "high", "critical"]

RelationType = Literal[
    "exposes",
    "attaches_to",
    "assumes_role",
    "reads_from",
    "writes_to",
    "encrypts",
    "monitors",
]


class GraphNode(BaseModel):
    id: str
    label: str
    category: CategoryType
    provider: str = "aws"
    severity: SeverityType = "clean"
    failing_controls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: RelationType
    is_attack_path: bool = False


class CriticalPath(BaseModel):
    path_id: str
    title: str
    severity: SeverityType
    description: str
    node_ids: list[str]


class AttackPathGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    toxic_combinations_count: int
    critical_paths: list[CriticalPath] = Field(default_factory=list)
    assessed_at: str | None = None

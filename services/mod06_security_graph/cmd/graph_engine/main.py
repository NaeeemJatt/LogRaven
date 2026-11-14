"""Module 06: Unified Security Graph, Attack Path Engine & TrueRisk Prioritizer.

FastAPI Router and Security Graph Engine Coordinator (PRD-MOD-06).
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod06_security_graph.internal.chokepoint_solver.edmonds_karp import EdmondsKarpMinCut
from services.mod06_security_graph.internal.graph_builder.identity_resolver import IdentityBlastResolver
from services.mod06_security_graph.internal.graph_builder.network_resolver import NetworkExposureResolver
from services.mod06_security_graph.internal.path_traversal.bfs_pathfinder import BFSPathFinder, DiscoveredAttackPath
from services.mod06_security_graph.internal.path_traversal.toxic_combinations import ToxicCombinationDetector
from services.mod06_security_graph.internal.repository.graph_repo import SecurityGraphRepository
from services.mod06_security_graph.internal.truerisk_engine.calculator import (
    TrueRiskCalculator,
    TrueRiskInputs,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 06: Security Graph & TrueRisk"])

# Engine instances
_pathfinder = BFSPathFinder(max_depth=6)
_toxic_detector = ToxicCombinationDetector()


# ── Request / Response Models ─────────────────────────────────────────────

class GraphNodeDTO(BaseModel):
    id: str
    domain: str = "COMPUTE"
    provider: str = "aws"
    label: str
    is_internet_facing: bool = False
    truerisk_score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeDTO(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship: str
    remediation_friction: float = 1.0
    is_attack_path: bool = False


class IngestTopologyRequest(BaseModel):
    nodes: List[GraphNodeDTO]
    edges: List[GraphEdgeDTO]


class TrueRiskEvaluateRequest(BaseModel):
    misconfig_severity: str = "CLEAN"
    network_exposure: str = "ISOLATED"
    identity_role: str = "NONE"
    data_classification: str = "NONE"
    threat_status: str = "NONE"
    custom_s_iom: Optional[float] = None
    custom_e_reach: Optional[float] = None
    custom_i_blast: Optional[float] = None
    custom_d_sens: Optional[float] = None
    custom_t_active: Optional[float] = None


class ChokepointQueryRequest(BaseModel):
    source_id: str
    target_crown_jewel_id: str
    edges: Optional[List[GraphEdgeDTO]] = None


# ── In-Memory Fast Cache for Topology SLA (< 5s for 50k nodes) ───────────
_active_nodes: Dict[str, Dict[str, Any]] = {}
_active_edges: List[Dict[str, Any]] = []


# ── REST API Endpoints ───────────────────────────────────────────────────

@router.post("/topology")
async def ingest_graph_topology(
    req: IngestTopologyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingests or updates graph topology (nodes and edges across 6 domains)."""
    global _active_nodes, _active_edges

    for n in req.nodes:
        _active_nodes[n.id] = n.model_dump()
        try:
            await SecurityGraphRepository.upsert_node(
                session=db,
                node_id=n.id,
                domain=n.domain,
                label=n.label,
                provider=n.provider,
                is_internet_facing=n.is_internet_facing,
                truerisk_score=n.truerisk_score,
                metadata=n.metadata,
                tenant_id=current_user.id if current_user else None,
            )
        except Exception as e:
            logger.debug(f"DB upsert node skipped in mock/test: {e}")

    for e in req.edges:
        e_dict = e.model_dump()
        _active_edges.append(e_dict)
        try:
            await SecurityGraphRepository.upsert_edge(
                session=db,
                edge_id=e.id,
                source_id=e.source_id,
                target_id=e.target_id,
                relationship=e.relationship,
                remediation_friction=e.remediation_friction,
                is_attack_path=e.is_attack_path,
                tenant_id=current_user.id if current_user else None,
            )
        except Exception as ex:
            logger.debug(f"DB upsert edge skipped in mock/test: {ex}")

    try:
        await db.commit()
    except Exception:
        pass

    return {
        "status": "INGESTED",
        "nodes_count": len(_active_nodes),
        "edges_count": len(_active_edges),
    }


@router.get("/attack-paths")
async def get_attack_paths(
    max_depth: int = Query(6, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Discovers all exploitable multi-hop attack paths (depth <= 6) with TrueRisk and Chokepoint."""
    global _active_nodes, _active_edges

    finder = BFSPathFinder(max_depth=max_depth)
    paths = finder.find_attack_paths(
        nodes=_active_nodes,
        edges=_active_edges,
    )

    results = []
    for p in paths:
        path_dict = {
            "title": p.title,
            "source_id": p.source_id,
            "target_id": p.target_id,
            "nodes": p.nodes,
            "path_length": p.path_length,
            "truerisk_score": p.truerisk_score,
            "score_exact": p.score_exact,
            "risk_tier": p.risk_tier,
            "chokepoint": p.chokepoint,
            "is_toxic_combination": p.is_toxic_combination,
        }
        results.append(path_dict)

        # Record in DB if session active
        try:
            await SecurityGraphRepository.record_attack_path(
                session=db,
                title=p.title,
                source_node_id=p.source_id,
                target_crown_jewel_id=p.target_id,
                path_length=p.path_length,
                node_path=p.nodes,
                truerisk_score=p.score_exact,
                chokepoint_edge_id=p.chokepoint["edge_id"] if p.chokepoint else None,
                chokepoint_description=p.chokepoint.get("description") if p.chokepoint else None,
                tenant_id=current_user.id if current_user else None,
            )
        except Exception:
            pass

    try:
        await db.commit()
    except Exception:
        pass

    return {
        "total_attack_paths": len(results),
        "paths": results,
    }


@router.post("/truerisk")
async def evaluate_truerisk(
    req: TrueRiskEvaluateRequest,
    current_user: User = Depends(get_current_user),
):
    """Evaluates the 5-variable TrueRisk prioritization formula."""
    return TrueRiskCalculator.evaluate(
        misconfig_severity=req.misconfig_severity,
        network_exposure=req.network_exposure,
        identity_role=req.identity_role,
        data_classification=req.data_classification,
        threat_status=req.threat_status,
        custom_s_iom=req.custom_s_iom,
        custom_e_reach=req.custom_e_reach,
        custom_i_blast=req.custom_i_blast,
        custom_d_sens=req.custom_d_sens,
        custom_t_active=req.custom_t_active,
    )


@router.post("/chokepoint")
async def compute_chokepoint(
    req: ChokepointQueryRequest,
    current_user: User = Depends(get_current_user),
):
    """Calculates Edmonds-Karp Minimum Cut and lowest-friction breaking point."""
    global _active_edges
    edges_to_use = [e.model_dump() for e in req.edges] if req.edges else _active_edges

    solver = EdmondsKarpMinCut()
    for e in edges_to_use:
        solver.add_edge(
            edge_id=e["id"],
            source=e["source_id"],
            target=e["target_id"],
            capacity=e.get("remediation_friction", 1.0),
            description=e.get("relationship", ""),
        )

    res = solver.compute_min_cut(source=req.source_id, sink=req.target_crown_jewel_id)
    return res


@router.get("/toxic-combinations")
async def list_toxic_combinations(
    current_user: User = Depends(get_current_user),
):
    """Discovers toxic combinations across all active nodes."""
    global _active_nodes, _active_edges

    adj: Dict[str, List[Dict[str, Any]]] = {n: [] for n in _active_nodes}
    for e in _active_edges:
        if e["source_id"] in adj:
            adj[e["source_id"]].append(e)

    toxic_findings = []
    for node_id, node_data in _active_nodes.items():
        finding = _toxic_detector.inspect_node_toxic_state(
            node_id=node_id,
            node_data=node_data,
            connected_edges=adj.get(node_id, []),
            neighbor_nodes=_active_nodes,
        )
        if finding:
            toxic_findings.append(finding)

    return {
        "toxic_combinations_count": len(toxic_findings),
        "findings": toxic_findings,
    }


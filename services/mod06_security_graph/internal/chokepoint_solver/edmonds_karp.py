"""Edmonds-Karp Minimum-Cut & Chokepoint Solver (FR-MOD6-04, TC-MOD6-001, TC-MOD6-002).

Constructs a flow network where edge capacity corresponds to remediation friction
(lower capacity = lower friction / easiest to sever). Computes the minimum s-t cut
that completely isolates the Crown Jewel from external threats with minimal operational disruption.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class FlowEdge:
    edge_id: str
    source: str
    target: str
    capacity: float
    description: str = ""
    flow: float = 0.0


class EdmondsKarpMinCut:
    """Computes Max-Flow and Minimum s-t Cut on security graph topologies."""

    def __init__(self):
        self.adj: Dict[str, List[str]] = {}
        self.capacity: Dict[Tuple[str, str], float] = {}
        self.flow: Dict[Tuple[str, str], float] = {}
        self.edge_metadata: Dict[Tuple[str, str], FlowEdge] = {}
        self.nodes: Set[str] = set()

    def add_edge(
        self,
        edge_id: str,
        source: str,
        target: str,
        capacity: float,
        description: str = "",
    ):
        """Adds a directed edge with remediation friction capacity to the flow network."""
        self.nodes.add(source)
        self.nodes.add(target)

        if source not in self.adj:
            self.adj[source] = []
        if target not in self.adj:
            self.adj[target] = []

        self.adj[source].append(target)
        self.adj[target].append(source)  # Backward residual edge

        self.capacity[(source, target)] = capacity
        self.capacity.setdefault((target, source), 0.0)

        self.flow[(source, target)] = 0.0
        self.flow[(target, source)] = 0.0

        edge_obj = FlowEdge(
            edge_id=edge_id,
            source=source,
            target=target,
            capacity=capacity,
            description=description,
        )
        self.edge_metadata[(source, target)] = edge_obj

    def add_node_capacity(
        self,
        node_id: str,
        capacity: float,
        description: str = "",
    ) -> Tuple[str, str]:
        """Splits node into (node_in, node_out) with internal bottleneck capacity."""
        node_in = f"{node_id}_in"
        node_out = f"{node_id}_out"
        self.add_edge(
            edge_id=f"node_internal_{node_id}",
            source=node_in,
            target=node_out,
            capacity=capacity,
            description=description or f"Remediate permissions on node {node_id}",
        )
        return node_in, node_out

    def _bfs_augmenting_path(
        self,
        source: str,
        sink: str,
        parent: Dict[str, Optional[str]],
    ) -> bool:
        """Finds shortest augmenting path from source to sink in residual graph."""
        for n in self.nodes:
            parent[n] = None

        parent[source] = source
        queue = deque([source])

        while queue:
            curr = queue.popleft()
            if curr == sink:
                return True

            for neighbor in self.adj.get(curr, []):
                residual = self.capacity.get((curr, neighbor), 0.0) - self.flow.get((curr, neighbor), 0.0)
                if residual > 1e-6 and parent[neighbor] is None:
                    parent[neighbor] = curr
                    queue.append(neighbor)

        return False

    def compute_min_cut(
        self,
        source: str,
        sink: str,
    ) -> Dict[str, Any]:
        """Calculates Edmonds-Karp max flow and returns the minimum s-t cut edges."""
        if source not in self.nodes or sink not in self.nodes:
            return {
                "max_flow": 0.0,
                "cut_edges": [],
                "chokepoint": None,
                "reachable_nodes": [],
            }

        # Reset flows
        for k in self.flow:
            self.flow[k] = 0.0

        parent: Dict[str, Optional[str]] = {}
        max_flow = 0.0

        # Augment flow along paths found by BFS
        while self._bfs_augmenting_path(source, sink, parent):
            # Find bottleneck residual capacity along path
            path_flow = float("inf")
            s = sink
            while s != source:
                p = parent[s]
                path_flow = min(path_flow, self.capacity[(p, s)] - self.flow[(p, s)])
                s = p

            # Apply bottleneck flow to path and reverse path
            v = sink
            while v != source:
                u = parent[v]
                self.flow[(u, v)] += path_flow
                self.flow[(v, u)] -= path_flow
                v = u

            max_flow += path_flow

        # BFS in final residual graph to identify reachable vertices from source
        visited: Set[str] = set()
        queue = deque([source])
        visited.add(source)

        while queue:
            curr = queue.popleft()
            for neighbor in self.adj.get(curr, []):
                residual = self.capacity.get((curr, neighbor), 0.0) - self.flow.get((curr, neighbor), 0.0)
                if residual > 1e-6 and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Edges in the original graph starting in visited (S) and ending in unvisited (T) form the Min-Cut
        cut_edges = []
        for (u, v), edge_data in self.edge_metadata.items():
            if u in visited and v not in visited and self.capacity.get((u, v), 0.0) > 0:
                cut_edges.append({
                    "edge_id": edge_data.edge_id,
                    "source": u,
                    "target": v,
                    "remediation_friction": edge_data.capacity,
                    "description": edge_data.description,
                })

        # Lowest-friction edge in cut is the primary remediation chokepoint
        chokepoint = None
        if cut_edges:
            cut_edges.sort(key=lambda e: e["remediation_friction"])
            chokepoint = cut_edges[0]

        return {
            "max_flow": max_flow,
            "cut_edges": cut_edges,
            "chokepoint": chokepoint,
            "reachable_nodes": list(visited),
        }


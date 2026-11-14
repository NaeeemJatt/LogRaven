"""Unit tests for Edmonds-Karp Minimum-Cut Solver (TC-MOD6-002, PRD-MOD-06)."""

import pytest
from services.mod06_security_graph.internal.chokepoint_solver.edmonds_karp import EdmondsKarpMinCut


def test_tc_mod6_002_edmonds_karp_diamond_shared_iam_role():
    """TC-MOD6-002: Run edmonds_karp on a multi-path diamond topology where 3 paths
    converge on a single IAM role.
    
    Pass Criteria: Solver outputs the shared IAM role as the minimum cut separating source from sink.
    """
    solver = EdmondsKarpMinCut()

    # Multi-path diamond graph:
    # 3 independent ingress vectors from Internet:
    # Path 1: internet -> ec2_web (capacity 10.0)
    # Path 2: internet -> api_gw (capacity 10.0)
    # Path 3: internet -> vpn_bastion (capacity 10.0)
    solver.add_edge("e_src_1", "internet", "ec2_web", capacity=10.0)
    solver.add_edge("e_src_2", "internet", "api_gw", capacity=10.0)
    solver.add_edge("e_src_3", "internet", "vpn_bastion", capacity=10.0)

    # All 3 paths converge on a single shared IAM role with node bottleneck
    role_in, role_out = solver.add_node_capacity(
        node_id="iam_role_prod_shared",
        capacity=2.0,  # Single permission policy boundary remediation friction
        description="Remediate overly permissive policy on shared IAM role",
    )

    solver.add_edge("e_web_role", "ec2_web", role_in, capacity=10.0)
    solver.add_edge("e_api_role", "api_gw", role_in, capacity=10.0)
    solver.add_edge("e_vpn_role", "vpn_bastion", role_in, capacity=10.0)

    # From shared IAM role to sensitive Crown Jewel storage
    solver.add_edge("e_role_s3", role_out, "s3_customer_pii", capacity=10.0)

    # Compute Min-Cut from internet to s3_customer_pii
    result = solver.compute_min_cut(source="internet", sink="s3_customer_pii")

    assert result["max_flow"] == 2.0, f"Expected max flow 2.0, got {result['max_flow']}"
    assert len(result["cut_edges"]) == 1, f"Expected exactly 1 cut edge, got {len(result['cut_edges'])}"

    chokepoint = result["chokepoint"]
    assert chokepoint is not None
    assert "iam_role_prod_shared" in chokepoint["source"] or "iam_role_prod_shared" in chokepoint["target"]
    assert chokepoint["remediation_friction"] == 2.0
    assert "Remediate overly permissive policy on shared IAM role" in chokepoint["description"]


def test_edmonds_karp_single_linear_chain():
    """Verifies that on a linear chain, the lowest capacity edge is chosen as chokepoint."""
    solver = EdmondsKarpMinCut()
    solver.add_edge("e1", "node_a", "node_b", capacity=10.0, description="Network link")
    solver.add_edge("e2", "node_b", "node_c", capacity=1.0, description="Revoke SG port 22")
    solver.add_edge("e3", "node_c", "node_d", capacity=15.0, description="Delete database")

    result = solver.compute_min_cut(source="node_a", sink="node_d")
    assert result["max_flow"] == 1.0
    assert result["chokepoint"]["edge_id"] == "e2"
    assert result["chokepoint"]["remediation_friction"] == 1.0

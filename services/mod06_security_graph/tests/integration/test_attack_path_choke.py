"""Integration tests for Multi-Hop Attack Path Discovery and Chokepoint Resolution (TC-MOD6-001, FR-MOD6-03, FR-MOD6-04)."""

import pytest
from services.mod06_security_graph.internal.path_traversal.bfs_pathfinder import BFSPathFinder
from services.mod06_security_graph.internal.path_traversal.toxic_combinations import ToxicCombinationDetector


def test_tc_mod6_001_four_node_attack_path_and_chokepoint():
    """TC-MOD6-001: Construct graph with 4 nodes:
    Internet -> EC2 (Port 22 open) -> IAM Role (Admin) -> S3 Bucket (PII).
    
    Pass Criteria:
    1. bfs_pathfinder detects attack path of length <= 6.
    2. TrueRisk score is >= 92 (Critical risk tier).
    3. Identifies Security Group rule as the lowest-friction breaking point.
    """
    pathfinder = BFSPathFinder(max_depth=6)

    # 4-node topology fixture
    nodes = {
        "internet_gateway": {
            "id": "internet_gateway",
            "domain": "NETWORK",
            "label": "Public Internet Gateway",
            "is_internet_facing": True,
            "metadata": {"has_open_ingress": True},
        },
        "ec2_prod_bastion": {
            "id": "ec2_prod_bastion",
            "domain": "COMPUTE",
            "label": "EC2 Bastion Host (i-0123456789abcdef0)",
            "is_internet_facing": True,
            "metadata": {
                "has_critical_vuln": True,
                "cve_count": 2,
                "severity": "CRITICAL",
                "open_ports": [22],
            },
        },
        "iam_role_admin": {
            "id": "iam_role_admin",
            "domain": "IDENTITY",
            "label": "IAM Role: ProductionAdminAccess",
            "is_internet_facing": False,
            "metadata": {
                "is_admin": True,
                "attached_policies": ["AdministratorAccess"],
            },
        },
        "s3_customer_pii": {
            "id": "s3_customer_pii",
            "domain": "DATA",
            "label": "S3 Bucket: prod-customer-pii-vault",
            "is_internet_facing": False,
            "metadata": {
                "is_crown_jewel": True,
                "has_pii": True,
                "data_classification": "PII_PCI_HIPAA",
            },
        },
    }

    edges = [
        {
            "id": "sg_ingress_rule_port_22",
            "source_id": "internet_gateway",
            "target_id": "ec2_prod_bastion",
            "relationship": "EXPOSES",
            "remediation_friction": 1.0,  # Lowest friction: 1-click revoke open SG rule
            "description": "Security Group rule allowing 0.0.0.0/0 ingress on SSH port 22",
        },
        {
            "id": "instance_profile_attachment",
            "source_id": "ec2_prod_bastion",
            "target_id": "iam_role_admin",
            "relationship": "ATTACHES_TO",
            "remediation_friction": 8.0,  # Medium/High friction: alters workload IAM credentials
            "description": "EC2 instance profile attaching administrative role",
        },
        {
            "id": "s3_full_access_policy",
            "source_id": "iam_role_admin",
            "target_id": "s3_customer_pii",
            "relationship": "READS_FROM",
            "remediation_friction": 15.0,  # High friction: breaking storage policy affects other services
            "description": "IAM policy granting broad read/write access to customer PII bucket",
        },
    ]

    # Execute BFS pathfinder
    paths = pathfinder.find_attack_paths(
        nodes=nodes,
        edges=edges,
        source_ids=["internet_gateway"],
        target_crown_jewel_ids=["s3_customer_pii"],
    )

    # 1. Assert path was detected
    assert len(paths) == 1, f"Expected 1 attack path, found {len(paths)}"
    path = paths[0]
    assert path.nodes == ["internet_gateway", "ec2_prod_bastion", "iam_role_admin", "s3_customer_pii"]
    assert path.path_length == 4

    # 2. Assert TrueRisk score >= 92
    assert path.truerisk_score >= 92, f"Expected TrueRisk score >= 92, got {path.truerisk_score}"
    assert path.risk_tier == "CRITICAL"
    assert path.is_toxic_combination is True

    # 3. Assert Security Group rule identified as lowest-friction breaking point
    chokepoint = path.chokepoint
    assert chokepoint is not None, "Failed to calculate chokepoint"
    assert chokepoint["edge_id"] == "sg_ingress_rule_port_22"
    assert chokepoint["remediation_friction"] == 1.0
    assert "Security Group rule" in chokepoint["description"]


def test_toxic_combination_detection_standalone():
    """Verifies ToxicCombinationDetector identifies hazardous node state."""
    detector = ToxicCombinationDetector()

    node_data = {
        "id": "ec2_app",
        "label": "Payment App EC2",
        "is_internet_facing": True,
        "metadata": {"has_critical_vuln": True, "cve_count": 1},
    }

    connected_edges = [
        {"source_id": "ec2_app", "target_id": "iam_admin"},
        {"source_id": "iam_admin", "target_id": "s3_pii"},
    ]

    neighbor_nodes = {
        "iam_admin": {
            "domain": "IDENTITY",
            "metadata": {"is_admin": True},
        },
        "s3_pii": {
            "domain": "DATA",
            "metadata": {"is_crown_jewel": True, "has_pii": True},
        },
    }

    finding = detector.inspect_node_toxic_state(
        node_id="ec2_app",
        node_data=node_data,
        connected_edges=connected_edges,
        neighbor_nodes=neighbor_nodes,
    )

    assert finding is not None
    assert finding["toxic_type"] == "INTERNET_EXPOSED_VULNERABLE_ADMIN"
    assert finding["severity"] == "CRITICAL"
    assert finding["truerisk_score"] >= 85


"""API integration tests for Module 06: Security Graph, Attack Path Engine & TrueRisk."""

import sys
if "ujson" not in sys.modules:
    sys.modules["ujson"] = None

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="graph-sec@lograven.io",
        name="Graph Security Architect",
        password_hash="argon2id$mocked$hash",
        email_verified=True,
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None), scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    return db


@pytest.mark.asyncio
async def test_ingest_topology_and_discover_attack_paths(test_user, mock_db):
    """Verifies ingesting 4-node attack path topology and retrieving attack paths via REST API."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    topology_payload = {
        "nodes": [
            {
                "id": "node_internet",
                "domain": "NETWORK",
                "label": "Internet Gateway",
                "provider": "aws",
                "is_internet_facing": True,
                "metadata": {"has_open_ingress": True},
            },
            {
                "id": "node_ec2",
                "domain": "COMPUTE",
                "label": "EC2 Production Bastion",
                "provider": "aws",
                "is_internet_facing": True,
                "metadata": {"has_critical_vuln": True, "cve_count": 3, "open_ports": [22]},
            },
            {
                "id": "node_iam_admin",
                "domain": "IDENTITY",
                "label": "IAM Role Administrator",
                "provider": "aws",
                "is_internet_facing": False,
                "metadata": {"is_admin": True},
            },
            {
                "id": "node_s3_pii",
                "domain": "DATA",
                "label": "Customer PII Bucket",
                "provider": "aws",
                "is_internet_facing": False,
                "metadata": {"is_crown_jewel": True, "has_pii": True},
            },
        ],
        "edges": [
            {
                "id": "e_open_ssh",
                "source_id": "node_internet",
                "target_id": "node_ec2",
                "relationship": "EXPOSES",
                "remediation_friction": 1.0,
            },
            {
                "id": "e_profile",
                "source_id": "node_ec2",
                "target_id": "node_iam_admin",
                "relationship": "ATTACHES_TO",
                "remediation_friction": 10.0,
            },
            {
                "id": "e_s3_read",
                "source_id": "node_iam_admin",
                "target_id": "node_s3_pii",
                "relationship": "READS_FROM",
                "remediation_friction": 20.0,
            },
        ],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 1. Ingest topology
        res_ingest = await client.post("/api/v1/security-graph/topology", json=topology_payload)
        assert res_ingest.status_code == 200
        data_ingest = res_ingest.json()
        assert data_ingest["status"] == "INGESTED"
        assert data_ingest["nodes_count"] >= 4

        # 2. Query attack paths
        res_paths = await client.get("/api/v1/security-graph/attack-paths")
        assert res_paths.status_code == 200
        data_paths = res_paths.json()
        assert data_paths["total_attack_paths"] >= 1
        top_path = data_paths["paths"][0]
        assert top_path["truerisk_score"] >= 92
        assert top_path["risk_tier"] == "CRITICAL"
        assert top_path["chokepoint"]["edge_id"] == "e_open_ssh"
        assert top_path["chokepoint"]["remediation_friction"] == 1.0

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_evaluate_truerisk_api(test_user):
    """Verifies /api/v1/security-graph/truerisk computes 5-variable score accurately."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    # TC-MOD6-003 scenario via REST API
    req_payload = {
        "custom_s_iom": 100.0,
        "custom_e_reach": 25.0,
        "custom_i_blast": 0.0,
        "custom_d_sens": 0.0,
        "custom_t_active": 0.0,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/security-graph/truerisk", json=req_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["score_exact"] == 31.25
        assert data["truerisk_score"] == 31
        assert data["risk_tier"] == "MEDIUM"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_compute_chokepoint_api(test_user):
    """Verifies /api/v1/security-graph/chokepoint calculates min-cut breaking point."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    payload = {
        "source_id": "attacker_entry",
        "target_crown_jewel_id": "crown_jewel_db",
        "edges": [
            {
                "id": "edge_ingress_sg",
                "source_id": "attacker_entry",
                "target_id": "intermediate_hop",
                "relationship": "EXPOSES",
                "remediation_friction": 1.5,
            },
            {
                "id": "edge_db_access",
                "source_id": "intermediate_hop",
                "target_id": "crown_jewel_db",
                "relationship": "READS_FROM",
                "remediation_friction": 12.0,
            },
        ],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/security-graph/chokepoint", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["max_flow"] == 1.5
        assert data["chokepoint"]["edge_id"] == "edge_ingress_sg"
        assert data["chokepoint"]["remediation_friction"] == 1.5

    app.dependency_overrides.clear()


"""Tests for Attack Path & Cloud Asset Relationship Graph."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.compliance.graph.builder import build_attack_path_graph
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.soc2_audit import AuditJob, CloudAccount


class _FakeDb:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.refresh = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock()

    def add(self, row):
        self.added.append(row)

    async def delete(self, row):
        self.deleted.append(row)


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class _ScalarsResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


@pytest.fixture
def fake_db():
    return _FakeDb()


@pytest.fixture
def client(fake_db):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="security_lead@acme.corp",
        tier="enterprise",
        password_hash="$2b$stub",
    )

    async def override_user():
        return user

    async def override_db():
        yield fake_db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c, user, fake_db
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_build_attack_path_graph_detects_toxic_combination():
    signals = {
        "open_security_groups": 2,
        "s3_public_access_blocked": False,
        "s3_default_encryption_rate": 50,
        "iam_admin_users": 3,
        "iam_stale_access_keys": 1,
        "ebs_default_encryption": False,
        "iam_root_mfa_enabled": False,
        "rds_encryption_rate": 80,
    }
    results = [
        {"control_id": "CC6.6", "status": "FAIL", "referenced_signals": ["open_security_groups"]},
        {"control_id": "CC6.7", "status": "FAIL", "referenced_signals": ["s3_public_access_blocked"]},
        {"control_id": "CC6.1", "status": "FAIL", "referenced_signals": ["iam_root_mfa_enabled"]},
    ]

    graph = build_attack_path_graph(signals, results)

    # 1. Structure assertions
    assert len(graph.nodes) >= 6
    assert len(graph.edges) >= 6

    # 2. Toxic combinations detected
    assert graph.toxic_combinations_count >= 2
    path_ids = [p.path_id for p in graph.critical_paths]
    assert "path-internet-to-s3-via-ssh" in path_ids
    assert "path-direct-s3-public-access" in path_ids

    # 3. Node risk attribution
    sg_node = next(n for n in graph.nodes if n.id == "net:sg_production")
    assert sg_node.severity == "critical"
    assert "CC6.6" in sg_node.failing_controls

    s3_node = next(n for n in graph.nodes if n.id == "storage:s3_customer_data")
    assert s3_node.severity == "critical"
    assert "CC6.7" in s3_node.failing_controls

    # 4. Attack path edge highlighting
    attack_edges = [e for e in graph.edges if e.is_attack_path]
    assert len(attack_edges) >= 3


def test_build_attack_path_graph_clean_posture():
    signals = {
        "open_security_groups": 0,
        "s3_public_access_blocked": True,
        "s3_default_encryption_rate": 100,
        "iam_admin_users": 0,
        "iam_stale_access_keys": 0,
        "ebs_default_encryption": True,
        "iam_root_mfa_enabled": True,
        "rds_encryption_rate": 100,
        "cloudtrail_multiregion": True,
        "guardduty_enabled": True,
    }
    results = [
        {"control_id": "CC6.6", "status": "PASS", "referenced_signals": ["open_security_groups"]},
        {"control_id": "CC6.7", "status": "PASS", "referenced_signals": ["s3_public_access_blocked"]},
        {"control_id": "CC6.1", "status": "PASS", "referenced_signals": ["iam_root_mfa_enabled"]},
    ]

    graph = build_attack_path_graph(signals, results)

    # No toxic combinations
    assert graph.toxic_combinations_count == 0
    assert len(graph.critical_paths) == 0

    # No attack path edges
    assert all(not e.is_attack_path for e in graph.edges)

    # All nodes clean
    for node in graph.nodes:
        if node.id != "net:internet":
            assert node.severity == "clean"


def test_get_audit_attack_path_graph_endpoint(client):
    c, user, db = client
    audit_id = uuid.uuid4()
    mock_job = SimpleNamespace(
        id=audit_id,
        evidence_signals={"open_security_groups": 1, "s3_public_access_blocked": True},
        results=[],
    )
    db.execute.return_value = _ScalarResult(mock_job)

    response = c.get(f"/api/v1/compliance/graph/audits/{audit_id}")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "toxic_combinations_count" in data
    assert len(data["nodes"]) >= 6


def test_get_account_attack_path_graph_endpoint(client):
    c, user, db = client
    account_id = uuid.uuid4()
    mock_account = SimpleNamespace(id=account_id, user_id=user.id, name="Production AWS")
    mock_job = SimpleNamespace(
        id=uuid.uuid4(),
        cloud_account_id=account_id,
        evidence_signals={"open_security_groups": 0, "s3_public_access_blocked": True},
        results=[],
    )

    def fake_execute(stmt):
        s = str(stmt)
        if "cloud_accounts" in s:
            return _ScalarResult(mock_account)
        elif "soc2_audit_jobs" in s:
            return _ScalarResult(mock_job)
        return _ScalarResult(None)

    db.execute.side_effect = fake_execute

    response = c.get(f"/api/v1/compliance/graph/accounts/{account_id}")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data

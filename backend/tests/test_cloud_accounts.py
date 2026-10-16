"""Tests for persistent cloud accounts and autonomous scan scheduling."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.compliance import accounts as accounts_routes
from app.compliance.scheduler import calculate_next_run, scan_due_cloud_accounts
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.soc2_audit import AuditJob, CloudAccount, ComplianceSnapshot


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

    def audit_actions(self) -> list[str]:
        return [r.action for r in self.added if isinstance(r, AuditLog)]


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
        email="lead@acme.corp",
        tier="pro",
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


def test_calculate_next_run_intervals():
    now = datetime.now(timezone.utc)
    daily = calculate_next_run("daily")
    weekly = calculate_next_run("weekly")
    monthly = calculate_next_run("monthly")
    none_run = calculate_next_run("none")

    assert none_run is None
    assert (daily - now).days == 1
    assert (weekly - now).days == 7
    assert (monthly - now).days == 30


def test_create_cloud_account_validates_arn_and_calculates_schedule(client):
    c, user, db = client

    # Invalid ARN format should fail validation
    invalid_resp = c.post(
        "/api/v1/compliance/accounts",
        json={
            "name": "Invalid Account",
            "role_arn": "not-an-arn",
            "scan_schedule": "weekly",
        },
    )
    assert invalid_resp.status_code == 422

    # Valid payload
    payload = {
        "name": "Acme AWS Production",
        "role_arn": "arn:aws:iam::123456789012:role/LogRavenAuditRole",
        "default_frameworks": ["soc2", "cis_aws"],
        "scan_schedule": "weekly",
    }

    r = c.post("/api/v1/compliance/accounts", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Acme AWS Production"
    assert data["account_id"] == "123456789012"
    assert data["provider"] == "aws"
    assert data["scan_schedule"] == "weekly"
    assert data["health_status"] == "connected"
    assert data["next_run_at"] is not None

    # Check persistence & audit logging
    created = [row for row in db.added if isinstance(row, CloudAccount)]
    assert len(created) == 1
    assert created[0].account_id == "123456789012"
    assert "compliance_account_added" in db.audit_actions()


def test_list_cloud_accounts_returns_latest_score(client):
    c, user, db = client
    acc_id = uuid.uuid4()
    account = CloudAccount(
        id=acc_id,
        user_id=user.id,
        name="Staging AWS",
        provider="aws",
        role_arn="arn:aws:iam::987654321098:role/AuditRole",
        account_id="987654321098",
        default_frameworks=["soc2"],
        scan_schedule="daily",
        health_status="connected",
        created_at=datetime.now(timezone.utc),
    )
    job = AuditJob(
        id=uuid.uuid4(),
        cloud_account_id=acc_id,
        status="complete",
        created_at=datetime.now(timezone.utc),
    )

    db.execute.side_effect = [
        _ScalarsResult([account]),  # list accounts
        _ScalarResult(job),         # latest audit
        _ScalarResult(85.5),        # avg score
    ]

    r = c.get("/api/v1/compliance/accounts")
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Staging AWS"
    assert data[0]["latest_score_percent"] == 85.5


def test_update_cloud_account_reschedules_next_run(client):
    c, user, db = client
    acc_id = uuid.uuid4()
    account = CloudAccount(
        id=acc_id,
        user_id=user.id,
        name="Old Name",
        provider="aws",
        role_arn="arn:aws:iam::123456789012:role/AuditRole",
        default_frameworks=["soc2"],
        scan_schedule="weekly",
        health_status="connected",
        created_at=datetime.now(timezone.utc),
    )

    db.execute.return_value = _ScalarResult(account)

    r = c.patch(
        f"/api/v1/compliance/accounts/{acc_id}",
        json={"name": "New Name", "scan_schedule": "daily"},
    )
    assert r.status_code == 200, r.text
    assert account.name == "New Name"
    assert account.scan_schedule == "daily"
    assert "compliance_account_updated" in db.audit_actions()


def test_delete_cloud_account_deletes_account_and_logs(client):
    c, user, db = client
    acc_id = uuid.uuid4()
    account = CloudAccount(
        id=acc_id,
        user_id=user.id,
        name="To Delete",
        role_arn="arn:aws:iam::123456789012:role/AuditRole",
        created_at=datetime.now(timezone.utc),
    )

    db.execute.return_value = _ScalarResult(account)

    r = c.delete(f"/api/v1/compliance/accounts/{acc_id}")
    assert r.status_code == 204
    assert account in db.deleted
    assert "compliance_account_deleted" in db.audit_actions()


def test_trigger_account_scan_creates_linked_audit_job(client, monkeypatch):
    c, user, db = client
    acc_id = uuid.uuid4()
    account = CloudAccount(
        id=acc_id,
        user_id=user.id,
        name="Production Core",
        role_arn="arn:aws:iam::123456789012:role/AuditRole",
        default_frameworks=["soc2"],
        scan_schedule="weekly",
        health_status="connected",
        created_at=datetime.now(timezone.utc),
    )

    db.execute.return_value = _ScalarResult(account)
    monkeypatch.setattr("app.tasks.dev_worker.ensure_dev_worker_running", lambda: True)

    from unittest.mock import MagicMock
    mock_task = MagicMock()
    monkeypatch.setattr("app.compliance.tasks.run_soc2_audit.apply_async", mock_task)

    r = c.post(f"/api/v1/compliance/accounts/{acc_id}/scan")
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["cloud_account_id"] == str(acc_id)
    assert data["status"] == "pending"

    # Verify AuditJob was queued with link
    audit_jobs = [row for row in db.added if isinstance(row, AuditJob)]
    assert len(audit_jobs) == 1
    assert audit_jobs[0].cloud_account_id == acc_id
    assert audit_jobs[0].company_name == "Production Core"


@pytest.mark.asyncio
async def test_scan_due_cloud_accounts_advances_schedule(monkeypatch):
    db = _FakeDb()
    now = datetime.now(timezone.utc)
    due_acc = CloudAccount(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Due AWS",
        role_arn="arn:aws:iam::123456789012:role/AuditRole",
        default_frameworks=["soc2"],
        scan_schedule="daily",
        next_run_at=now - timedelta(hours=1),
        health_status="connected",
    )

    db.execute.return_value = _ScalarsResult([due_acc])
    monkeypatch.setattr("app.tasks.dev_worker.ensure_dev_worker_running", lambda: False)

    started_ids = await scan_due_cloud_accounts(db)
    assert len(started_ids) == 1

    # Verify schedule was advanced to tomorrow
    assert due_acc.next_run_at > now
    assert (due_acc.next_run_at - now).days == 1

    # Verify AuditJob was added
    audit_jobs = [row for row in db.added if isinstance(row, AuditJob)]
    assert len(audit_jobs) == 1
    assert audit_jobs[0].cloud_account_id == due_acc.id

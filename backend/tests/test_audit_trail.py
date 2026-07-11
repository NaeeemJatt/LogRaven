# LogRaven — Tests: audit-trail coverage for lifecycle, compliance and password actions

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.audit import AuditLog
from app.utils.audit import add_audit


class _FakeDb:
    """Records added rows; async no-ops for commit/flush/refresh/rollback."""

    def __init__(self):
        self.added = []
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.refresh = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock()

    def add(self, row):
        self.added.append(row)

    def audit_actions(self) -> list[str]:
        return [r.action for r in self.added if isinstance(r, AuditLog)]


def _fake_user(tier="free"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="u@example.com",
        tier=tier,
        password_hash="$2b$stub",
    )


@pytest.fixture
def fake_db():
    return _FakeDb()


@pytest.fixture
def client(fake_db):
    user = _fake_user()

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


# ── add_audit helper ──────────────────────────────────────────────────────────

def test_add_audit_queues_row_with_request_context(fake_db):
    request = SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.9"),
        headers={"user-agent": "pytest-agent"},
    )
    user_id = uuid.uuid4()

    add_audit(fake_db, user_id=user_id, action="analyze", request=request, metadata={"k": "v"})

    assert len(fake_db.added) == 1
    row = fake_db.added[0]
    assert isinstance(row, AuditLog)
    assert row.user_id == user_id
    assert row.action == "analyze"
    assert row.ip_address == "203.0.113.9"
    assert row.user_agent == "pytest-agent"
    assert row.metadata_ == {"k": "v"}


def test_add_audit_tolerates_missing_request(fake_db):
    add_audit(fake_db, user_id=None, action="account_deleted", request=None, metadata={})
    row = fake_db.added[0]
    assert row.ip_address is None
    assert row.user_agent is None


# ── Password change ───────────────────────────────────────────────────────────

def test_password_change_is_audit_logged(client, monkeypatch):
    c, user, db = client
    monkeypatch.setattr("app.utils.security.verify_password", lambda *a: True)
    monkeypatch.setattr("app.utils.security.hash_password", lambda p: "$2b$new")

    r = c.post(
        "/auth/password/change",
        json={"current_password": "old-password", "new_password": "new-password-123"},
    )

    assert r.status_code == 204, r.text
    assert db.audit_actions() == ["password_changed"]


def test_failed_password_change_is_not_audit_logged(client, monkeypatch):
    c, user, db = client
    monkeypatch.setattr("app.utils.security.verify_password", lambda *a: False)

    r = c.post(
        "/auth/password/change",
        json={"current_password": "wrong", "new_password": "new-password-123"},
    )

    assert r.status_code == 400
    assert db.audit_actions() == []


# ── Investigation lifecycle ───────────────────────────────────────────────────

def test_create_investigation_is_audit_logged(client):
    c, user, db = client

    from datetime import datetime

    # Second execute call re-fetches with relationships; return a stub investigation.
    inv = SimpleNamespace(
        id=uuid.uuid4(), user_id=user.id, name="Audit trail check",
        status="draft", progress_stage=None, error_message=None,
        correlation_enabled=True, created_at=datetime.utcnow(), completed_at=None,
        queued_at=None, files=[], report=None,
    )
    db.execute.return_value = SimpleNamespace(scalar_one=lambda: inv)

    r = c.post("/api/v1/investigations", json={"name": "Audit trail check"})

    assert r.status_code == 201, r.text
    assert "investigation_created" in db.audit_actions()
    created = next(
        row for row in db.added
        if isinstance(row, AuditLog) and row.action == "investigation_created"
    )
    assert created.metadata_["name"] == "Audit trail check"
    assert created.user_id == user.id


def test_delete_investigation_is_audit_logged(client):
    c, user, db = client
    inv_id = uuid.uuid4()
    inv = SimpleNamespace(
        id=inv_id, user_id=user.id, name="Doomed", status="draft",
        files=[], report=None,
    )
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: inv),    # ownership lookup
        SimpleNamespace(scalar_one_or_none=lambda: None),   # report pdf key lookup
    ]
    db.delete = AsyncMock()

    r = c.delete(f"/api/v1/investigations/{inv_id}")

    assert r.status_code == 204, r.text
    assert "investigation_deleted" in db.audit_actions()


def test_delete_file_is_audit_logged(client, monkeypatch):
    from app.dependencies import get_storage

    c, user, db = client
    inv_id, file_id = uuid.uuid4(), uuid.uuid4()
    inv = SimpleNamespace(id=inv_id, user_id=user.id, status="draft")
    inv_file = SimpleNamespace(
        id=file_id, investigation_id=inv_id,
        filename="auth.log", storage_key="uploads/x/auth.log",
    )
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: inv),
        SimpleNamespace(scalar_one_or_none=lambda: inv_file),
    ]
    db.delete = AsyncMock()
    storage = SimpleNamespace(delete_file=AsyncMock())
    app.dependency_overrides[get_storage] = lambda: storage
    try:
        r = c.delete(f"/api/v1/investigations/{inv_id}/files/{file_id}")
    finally:
        app.dependency_overrides.pop(get_storage, None)

    assert r.status_code == 204, r.text
    assert "file_deleted" in db.audit_actions()
    deleted = next(
        row for row in db.added
        if isinstance(row, AuditLog) and row.action == "file_deleted"
    )
    assert deleted.metadata_["filename"] == "auth.log"


# ── Compliance actions ────────────────────────────────────────────────────────

def _completed_audit_job(user_id):
    return SimpleNamespace(
        id=uuid.uuid4(), user_id=user_id, status="complete",
        company_name="Acme Corp", role_arn="arn:aws:iam::123456789012:role/Audit",
        audit_start_date=date(2026, 1, 1), audit_end_date=date(2026, 6, 1),
        frameworks=["soc2"], recurrence="none",
        report_keys={}, pdf_storage_key=None, evidence_signals={},
    )


def test_compliance_share_is_audit_logged(client, monkeypatch):
    c, user, db = client
    job = _completed_audit_job(user.id)
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: job)
    monkeypatch.setattr(
        "app.utils.security.create_audit_share_token", lambda *a, **k: "tok123"
    )

    r = c.post(f"/api/v1/audit/{job.id}/share")

    assert r.status_code == 200, r.text
    assert "compliance_audit_shared" in db.audit_actions()


def test_compliance_evidence_download_is_audit_logged(client):
    c, user, db = client
    job = _completed_audit_job(user.id)
    result_row = SimpleNamespace(
        framework="soc2", control_id="CC6.1", control_name="Logical access",
        status="PASS", ai_description="ok", raw_evidence_summary={},
    )
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: job),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [result_row])),
    ]

    r = c.get(f"/api/v1/audit/{job.id}/evidence")

    assert r.status_code == 200, r.text
    assert "compliance_evidence_downloaded" in db.audit_actions()


def test_compliance_start_is_audit_logged(client, monkeypatch):
    c, user, db = client
    monkeypatch.setattr(
        "app.api.compliance.routes.run_soc2_audit",
        SimpleNamespace(apply_async=lambda *a, **k: SimpleNamespace(id="task-1")),
    )

    r = c.post(
        "/api/v1/audit/start",
        json={
            "company_name": "Acme Corp",
            "role_arn": "arn:aws:iam::123456789012:role/Audit",
            "audit_start_date": "2026-01-01",
            "audit_end_date": "2026-06-01",
            "frameworks": ["soc2"],
        },
    )

    assert r.status_code == 201, r.text
    assert "compliance_audit_started" in db.audit_actions()

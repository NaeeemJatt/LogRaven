"""Tests for external CPA Auditor Portal and Cryptographic Evidence Vault."""

import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.compliance import auditor as auditor_routes
from app.compliance.vault import build_evidence_vault_zip
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.soc2_audit import AuditJob, AuditResult, AuditorAccessToken, ComplianceException


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
        email="compliance_officer@acme.corp",
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


def test_build_evidence_vault_zip_structure_and_sha256_integrity():
    now = datetime.now(timezone.utc)
    mock_result = SimpleNamespace(
        control_id="CC6.1",
        control_name="Logical Access Controls",
        status="PASS",
        framework="soc2",
        evidence_summary="IAM password policy enforces 14-char length and MFA.",
        remediation="Ensure all users have MFA.",
        referenced_signals=["iam_mfa_active"],
        assessed_at=now,
    )
    mock_job = SimpleNamespace(
        id=uuid.uuid4(),
        status="complete",
        frameworks=["soc2"],
        score_percent=95.0,
        raw_score_percent=90.0,
        completed_at=now,
        results=[mock_result],
        evidence_signals={"iam_root_mfa": True},
    )
    mock_exception = SimpleNamespace(
        control_id="CC6.6",
        framework="soc2",
        status="ACTIVE",
        justification="Bastion host SSH restricted to corporate VPN.",
        compensating_controls="WireGuard VPN with Cisco Duo MFA.",
        authorized_by="CISO Alice",
        expires_at=now + timedelta(days=90),
        created_at=now,
    )

    zip_bytes, zip_filename = build_evidence_vault_zip(
        company_name="Acme Corp",
        audit_jobs=[mock_job],
        exceptions=[mock_exception],
    )

    assert zip_filename.startswith("LogRaven_Evidence_Vault_Acme_Corp_")
    assert zip_filename.endswith(".zip")

    # Inspect zip contents
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "00_AUDITOR_README.txt" in namelist
        assert "01_Executive_Summary.json" in namelist
        assert "02_Business_Logic_Exceptions_Ledger.csv" in namelist
        assert "Criteria_CC6_Logical_and_Physical_Access/CC6_1_evidence.json" in namelist
        assert "Raw_Telemetry_Snapshots/evidence_signals.json" in namelist
        assert "SHA256_INTEGRITY_MANIFEST.txt" in namelist

        # Strict Cryptographic Verification: Verify every file against the manifest
        manifest_data = zf.read("SHA256_INTEGRITY_MANIFEST.txt").decode("utf-8")
        manifest_lines = [line.strip() for line in manifest_data.strip().split("\n") if line.strip()]

        manifest_dict = {}
        for line in manifest_lines:
            digest, filepath = line.split("  ")
            manifest_dict[filepath] = digest

        for filepath, expected_digest in manifest_dict.items():
            file_bytes = zf.read(filepath)
            computed_digest = hashlib.sha256(file_bytes).hexdigest()
            assert computed_digest == expected_digest, f"Checksum mismatch for {filepath}"


def test_create_auditor_token_authenticated(client):
    c, user, db = client

    response = c.post(
        "/api/v1/compliance/auditor/tokens",
        json={
            "company_name": "Acme Corp",
            "recipient_name": "Sarah Jenkins",
            "recipient_email": "sarah@schellman.com",
            "passcode": "Audit2026!",
            "duration_days": 30,
            "allowed_frameworks": ["soc2", "iso27001"],
            "can_download_raw_evidence": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "token" in data
    assert data["company_name"] == "Acme Corp"
    assert data["recipient_name"] == "Sarah Jenkins"

    # Check token was hashed before storing in DB
    created = next(r for r in db.added if isinstance(r, AuditorAccessToken))
    assert created.token_hash != data["token"]
    assert created.token_hash == hashlib.sha256(data["token"].encode()).hexdigest()
    assert created.passcode_hash == hashlib.sha256("Audit2026!".encode()).hexdigest()
    assert "create_auditor_token" in db.audit_actions()


def test_list_auditor_tokens(client):
    c, user, db = client
    now = datetime.now(timezone.utc)
    mock_token = AuditorAccessToken(
        id=uuid.uuid4(),
        user_id=user.id,
        company_name="Acme Corp",
        token_hash="fakehash",
        recipient_name="John CPA",
        recipient_email="john@align.com",
        allowed_frameworks=["soc2"],
        can_download_raw_evidence=True,
        expires_at=now + timedelta(days=15),
        revoked_at=None,
        access_count=2,
        last_accessed_at=now,
        created_at=now,
    )
    db.execute.return_value = _ScalarsResult([mock_token])

    response = c.get("/api/v1/compliance/auditor/tokens")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["recipient_name"] == "John CPA"
    assert data[0]["access_count"] == 2
    assert not data[0]["is_expired"]
    assert not data[0]["is_revoked"]


def test_revoke_auditor_token(client):
    c, user, db = client
    token_id = uuid.uuid4()
    mock_token = AuditorAccessToken(
        id=token_id,
        user_id=user.id,
        company_name="Acme Corp",
        token_hash="fakehash",
        access_count=0,
        expires_at=datetime.now(timezone.utc) + timedelta(days=15),
        revoked_at=None,
    )
    db.execute.return_value = _ScalarResult(mock_token)

    response = c.delete(f"/api/v1/compliance/auditor/tokens/{token_id}")
    assert response.status_code == 204
    assert mock_token.revoked_at is not None
    assert "revoke_auditor_token" in db.audit_actions()


def test_verify_auditor_token_portal(client):
    c, user, db = client
    now = datetime.now(timezone.utc)
    plain_token = "valid_secret_auditor_token_12345"
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    passcode_hash = hashlib.sha256("ValidPasscode123".encode()).hexdigest()

    mock_token = AuditorAccessToken(
        id=uuid.uuid4(),
        user_id=user.id,
        company_name="Acme Corp",
        token_hash=token_hash,
        passcode_hash=passcode_hash,
        expires_at=now + timedelta(days=10),
        revoked_at=None,
        access_count=0,
        allowed_frameworks=["soc2"],
        can_download_raw_evidence=True,
    )
    db.execute.return_value = _ScalarResult(mock_token)

    # 1. Invalid Passcode fails
    res_bad = c.post(
        "/api/v1/compliance/auditor/portal/verify",
        json={"token": plain_token, "passcode": "WrongPassword"},
    )
    assert res_bad.status_code == 401

    # 2. Correct Passcode succeeds
    res_good = c.post(
        "/api/v1/compliance/auditor/portal/verify",
        json={"token": plain_token, "passcode": "ValidPasscode123"},
    )
    assert res_good.status_code == 200
    data = res_good.json()
    assert data["valid"] is True
    assert data["company_name"] == "Acme Corp"
    assert mock_token.access_count == 1


def test_auditor_portal_overview_and_exceptions(client):
    c, user, db = client
    now = datetime.now(timezone.utc)
    plain_token = "portal_overview_token_abcdef12345"
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

    mock_token = AuditorAccessToken(
        id=uuid.uuid4(),
        user_id=user.id,
        company_name="Acme Corp",
        token_hash=token_hash,
        passcode_hash=None,
        expires_at=now + timedelta(days=10),
        revoked_at=None,
        access_count=0,
        allowed_frameworks=["soc2"],
        can_download_raw_evidence=True,
    )

    mock_result = SimpleNamespace(status="PASS", control_id="CC6.1")
    mock_job = SimpleNamespace(
        id=uuid.uuid4(),
        company_name="Acme Corp",
        status="complete",
        frameworks=["soc2"],
        score_percent=92.0,
        raw_score_percent=88.0,
        completed_at=now,
        results=[mock_result],
    )
    mock_exc = SimpleNamespace(
        id=uuid.uuid4(),
        control_id="CC6.6",
        framework="soc2",
        status="ACTIVE",
        justification="VPC VPN gateway in place",
        compensating_controls="WireGuard",
        authorized_by="Lead SecOps",
        expires_at=now + timedelta(days=60),
        created_at=now,
    )

    def fake_execute(stmt):
        s = str(stmt)
        if "soc2_audit_jobs" in s:
            return _ScalarsResult([mock_job])
        elif "compliance_exceptions" in s:
            return _ScalarsResult([mock_exc])
        return _ScalarResult(mock_token)

    db.execute.side_effect = fake_execute

    # Overview endpoint
    overview_res = c.get(f"/api/v1/compliance/auditor/portal/{plain_token}/overview")
    assert overview_res.status_code == 200
    ov_data = overview_res.json()
    assert ov_data["company_name"] == "Acme Corp"
    assert ov_data["latest_audit"]["score_percent"] == 92.0
    assert ov_data["active_exceptions_count"] == 1

    # Exceptions endpoint
    exc_res = c.get(f"/api/v1/compliance/auditor/portal/{plain_token}/exceptions")
    assert exc_res.status_code == 200
    exc_data = exc_res.json()
    assert len(exc_data) == 1
    assert exc_data[0]["control_id"] == "CC6.6"
    assert exc_data[0]["authorized_by"] == "Lead SecOps"


def test_auditor_portal_download_evidence_vault(client):
    c, user, db = client
    now = datetime.now(timezone.utc)
    plain_token = "download_vault_token_987654321"
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

    mock_token = AuditorAccessToken(
        id=uuid.uuid4(),
        user_id=user.id,
        company_name="Acme Corp",
        token_hash=token_hash,
        passcode_hash=None,
        expires_at=now + timedelta(days=10),
        revoked_at=None,
        access_count=0,
        allowed_frameworks=["soc2"],
        can_download_raw_evidence=True,
    )

    mock_job = SimpleNamespace(
        id=uuid.uuid4(),
        company_name="Acme Corp",
        status="complete",
        frameworks=["soc2"],
        score_percent=95.0,
        raw_score_percent=90.0,
        completed_at=now,
        results=[],
        evidence_signals={},
    )

    def fake_execute(stmt):
        s = str(stmt)
        if "soc2_audit_jobs" in s:
            return _ScalarsResult([mock_job])
        elif "compliance_exceptions" in s:
            return _ScalarsResult([])
        return _ScalarResult(mock_token)

    db.execute.side_effect = fake_execute

    vault_res = c.get(f"/api/v1/compliance/auditor/portal/{plain_token}/evidence-vault")
    assert vault_res.status_code == 200
    assert vault_res.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in vault_res.headers["content-disposition"]

    # Read streamed bytes as zip
    with zipfile.ZipFile(io.BytesIO(vault_res.content), "r") as zf:
        assert "00_AUDITOR_README.txt" in zf.namelist()
        assert "SHA256_INTEGRITY_MANIFEST.txt" in zf.namelist()

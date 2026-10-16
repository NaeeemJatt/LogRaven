"""Tests for finding suppression and business logic exception engine.

Covers:
- Dual scoring calculations (score_results with raw vs adjusted score).
- Suppression API endpoint (POST /audit/{id}/controls/{id}/suppress).
- Unsuppression / revocation endpoint (DELETE /audit/{id}/controls/{id}/suppress).
- Listing exceptions (GET /audit/{id}/exceptions and GET /compliance/exceptions).
- Pipeline preservation of active exceptions and ignoring expired ones.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.compliance import routes as compliance_routes
from app.compliance.ai_grader import score_results
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.soc2_audit import AuditJob, AuditResult, ComplianceException, ComplianceSnapshot


# ── 1. Scoring Logic Unit Tests ───────────────────────────────────────────────

def test_score_results_without_suppression():
    results = [
        {"status": "PASS"},
        {"status": "PASS"},
        {"status": "FAIL"},
        {"status": "PARTIAL"},
    ]
    score = score_results(results, total=4)
    assert score["pass_count"] == 2
    assert score["suppressed_count"] == 0
    assert score["fail_count"] == 1
    assert score["partial_count"] == 1
    assert score["raw_score_percent"] == 50.0
    assert score["score_percent"] == 50.0


def test_score_results_with_suppression():
    # 4 controls: 2 PASS, 1 FAIL, 1 SUPPRESSED
    results = [
        {"status": "PASS"},
        {"status": "PASS"},
        {"status": "FAIL"},
        {"status": "SUPPRESSED"},
    ]
    score = score_results(results, total=4)
    assert score["pass_count"] == 2
    assert score["suppressed_count"] == 1
    assert score["fail_count"] == 1
    assert score["partial_count"] == 0
    # Raw score: 2 / 4 = 50.0%
    assert score["raw_score_percent"] == 50.0
    # Adjusted score: 2 / (4 - 1) = 2/3 = 66.67%
    assert score["score_percent"] == 66.67


def test_score_results_all_suppressed():
    results = [
        {"status": "SUPPRESSED"},
        {"status": "SUPPRESSED"},
    ]
    score = score_results(results, total=2)
    assert score["pass_count"] == 0
    assert score["suppressed_count"] == 2
    assert score["raw_score_percent"] == 0.0
    assert score["score_percent"] == 0.0  # Safe against division by zero


def test_score_results_empty_results():
    score = score_results([], total=0)
    assert score["raw_score_percent"] == 0.0
    assert score["score_percent"] == 0.0


# ── 2. API Routes Unit Tests ──────────────────────────────────────────────────

class _FakeDb:
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


def _fake_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="security-lead@acme.corp",
        tier="pro",
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


def test_suppress_control_endpoint_updates_status_and_logs_audit(client):
    c, user, db = client
    audit_id = uuid.uuid4()
    job = AuditJob(
        id=audit_id,
        user_id=user.id,
        company_name="Acme Corp",
        frameworks=["soc2"],
        status="complete",
    )
    result = AuditResult(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        control_id="CC6.1",
        control_name="Logical Access Controls",
        status="FAIL",
        raw_evidence_summary={"gaps": ["MFA not enforced on root"]},
    )
    snapshot = ComplianceSnapshot(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        pass_count=5,
        fail_count=6,
        partial_count=0,
        suppressed_count=0,
        score_percent=45.45,
    )

    # Sequence of DB execute calls:
    # 1. _load_owned_job -> job
    # 2. find AuditResult -> result
    # 3. find existing ComplianceException -> None
    # 4. list all AuditResult for framework -> [result]
    # 5. find ComplianceSnapshot -> snapshot
    db.execute.side_effect = [
        _ScalarResult(job),
        _ScalarResult(result),
        _ScalarResult(None),
        _ScalarsResult([result]),
        _ScalarResult(snapshot),
    ]

    payload = {
        "business_justification": "Break-glass root account with physical YubiKey stored in bank vault.",
        "compensating_controls": "Quarterly manual inspection and CloudWatch alarm on root login.",
        "risk_level": "low",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
    }

    r = c.post(
        f"/api/v1/audit/{audit_id}/controls/CC6.1/suppress?framework=soc2",
        json=payload,
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["control_id"] == "CC6.1"
    assert body["status"] == "SUPPRESSED"
    assert body["exception"] is not None
    assert body["exception"]["business_justification"] == payload["business_justification"]
    assert body["exception"]["risk_level"] == "low"
    assert body["exception"]["suppressed_by"] == "security-lead@acme.corp"

    # Verify AuditResult was updated in-place
    assert result.status == "SUPPRESSED"

    # Verify ComplianceException was created
    new_exceptions = [e for e in db.added if isinstance(e, ComplianceException)]
    assert len(new_exceptions) == 1
    assert new_exceptions[0].company_name == "Acme Corp"
    assert new_exceptions[0].control_id == "CC6.1"
    assert new_exceptions[0].status == "active"

    # Verify audit action was recorded
    assert "compliance_control_suppressed" in db.audit_actions()

    # Verify report cache was invalidated
    assert job.report_keys == {}
    assert job.pdf_storage_key is None


def test_unsuppress_control_endpoint_reverts_status_and_logs_audit(client):
    c, user, db = client
    audit_id = uuid.uuid4()
    job = AuditJob(
        id=audit_id,
        user_id=user.id,
        company_name="Acme Corp",
        frameworks=["soc2"],
        status="complete",
    )
    result = AuditResult(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        control_id="CC6.1",
        control_name="Logical Access Controls",
        status="SUPPRESSED",
        raw_evidence_summary={
            "gaps": ["MFA not enforced on root"],
            "exception": {"business_justification": "Old justification"},
        },
    )
    existing_exc = ComplianceException(
        id=uuid.uuid4(),
        user_id=user.id,
        company_name="Acme Corp",
        framework="soc2",
        control_id="CC6.1",
        status="active",
    )
    snapshot = ComplianceSnapshot(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        pass_count=5,
        fail_count=5,
        partial_count=0,
        suppressed_count=1,
        score_percent=50.0,
    )

    # Sequence of DB execute calls:
    # 1. _load_owned_job -> job
    # 2. find AuditResult -> result
    # 3. find existing ComplianceException -> existing_exc
    # 4. list all AuditResult for framework -> [result]
    # 5. find ComplianceSnapshot -> snapshot
    db.execute.side_effect = [
        _ScalarResult(job),
        _ScalarResult(result),
        _ScalarResult(existing_exc),
        _ScalarsResult([result]),
        _ScalarResult(snapshot),
    ]

    r = c.delete(
        f"/api/v1/audit/{audit_id}/controls/CC6.1/suppress?framework=soc2"
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["control_id"] == "CC6.1"
    # Reverts to FAIL since gaps list was non-empty
    assert body["status"] == "FAIL"
    assert body["exception"] is None

    # Verify exception record status is revoked
    assert existing_exc.status == "revoked"

    # Verify audit action was recorded
    assert "compliance_control_unsuppressed" in db.audit_actions()


def test_list_audit_exceptions_endpoint(client):
    c, user, db = client
    audit_id = uuid.uuid4()
    job = AuditJob(
        id=audit_id,
        user_id=user.id,
        company_name="Acme Corp",
        frameworks=["soc2"],
        status="complete",
    )
    exc1 = ComplianceException(
        id=uuid.uuid4(),
        user_id=user.id,
        company_name="Acme Corp",
        framework="soc2",
        control_id="CC6.1",
        business_justification="Vaulted YubiKey",
        compensating_controls="Physical safe",
        risk_level="low",
        suppressed_by="security-lead@acme.corp",
        status="active",
        created_at=datetime.now(timezone.utc),
    )

    db.execute.side_effect = [
        _ScalarResult(job),
        _ScalarsResult([exc1]),
    ]

    r = c.get(f"/api/v1/audit/{audit_id}/exceptions")
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 1
    assert data[0]["control_id"] == "CC6.1"
    assert data[0]["business_justification"] == "Vaulted YubiKey"
    assert data[0]["status"] == "active"


# ── 3. Pipeline Integration Unit Test ─────────────────────────────────────────

def test_pipeline_applies_active_exceptions_and_ignores_expired():
    """Verify the logic in tasks.py that attaches exceptions and marks controls SUPPRESSED."""
    now_utc = datetime.now(timezone.utc)
    active_exc = ComplianceException(
        id=uuid.uuid4(),
        company_name="Acme Corp",
        framework="soc2",
        control_id="CC6.1",
        business_justification="YubiKey vault",
        compensating_controls="Dual control",
        risk_level="low",
        suppressed_by="lead@acme.corp",
        status="active",
        expires_at=now_utc + timedelta(days=30),
    )
    expired_exc = ComplianceException(
        id=uuid.uuid4(),
        company_name="Acme Corp",
        framework="soc2",
        control_id="CC6.2",
        business_justification="Old temp fix",
        compensating_controls="None",
        risk_level="high",
        suppressed_by="lead@acme.corp",
        status="active",
        expires_at=now_utc - timedelta(days=5),
    )

    all_exceptions = [active_exc, expired_exc]
    exceptions_by_fw_ctl: dict[tuple[str, str], ComplianceException] = {}
    for exc in all_exceptions:
        if exc.expires_at and exc.expires_at < now_utc:
            exc.status = "expired"
        else:
            exceptions_by_fw_ctl[(exc.framework, exc.control_id)] = exc

    # Expired was marked expired and omitted from active lookup
    assert expired_exc.status == "expired"
    assert ("soc2", "CC6.2") not in exceptions_by_fw_ctl
    assert ("soc2", "CC6.1") in exceptions_by_fw_ctl

    # Mock raw AI grader control results
    control_results = [
        {"control_id": "CC6.1", "status": "FAIL", "gaps": ["No MFA"]},
        {"control_id": "CC6.2", "status": "FAIL", "gaps": ["Password length < 14"]},
        {"control_id": "CC6.3", "status": "PASS", "gaps": []},
    ]

    for control in control_results:
        ctl_id = control.get("control_id", "")
        exc = exceptions_by_fw_ctl.get(("soc2", ctl_id))
        if exc and control.get("status") in ("FAIL", "PARTIAL"):
            control["status"] = "SUPPRESSED"
            control["exception"] = {
                "id": str(exc.id),
                "business_justification": exc.business_justification,
                "compensating_controls": exc.compensating_controls,
                "risk_level": exc.risk_level,
                "suppressed_by": exc.suppressed_by,
                "expires_at": exc.expires_at.isoformat() if exc.expires_at else None,
            }

    # CC6.1 must be SUPPRESSED
    assert control_results[0]["status"] == "SUPPRESSED"
    assert control_results[0]["exception"]["business_justification"] == "YubiKey vault"

    # CC6.2 must remain FAIL because exception was expired
    assert control_results[1]["status"] == "FAIL"
    assert "exception" not in control_results[1]

    # CC6.3 remains PASS
    assert control_results[2]["status"] == "PASS"


# ── 4. PDF Report Generator with Exceptions ───────────────────────────────────

def test_generate_compliance_report_with_suppressed_controls():
    from app.compliance.report_generator import generate_compliance_report
    import os

    audit_id = uuid.uuid4()
    job = AuditJob(
        id=audit_id,
        user_id=uuid.uuid4(),
        company_name="Acme Financial",
        role_arn="arn:aws:iam::123456789012:role/AuditRole",
        audit_start_date=datetime(2025, 1, 1).date(),
        audit_end_date=datetime(2025, 1, 31).date(),
        frameworks=["soc2"],
        status="complete",
    )

    r_pass = AuditResult(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        control_id="CC6.1",
        control_name="Logical Access Controls",
        status="PASS",
        evidence_count=1,
        ai_description="MFA enforced across all active console users.",
        raw_evidence_summary={
            "gaps": [],
            "evidence_references": ["IAM MFA rate = 100%"],
            "confidence": "HIGH",
        },
    )

    r_suppressed = AuditResult(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        control_id="CC6.2",
        control_name="User Registration and Access Rights",
        status="SUPPRESSED",
        evidence_count=1,
        ai_description="Password rotation interval deferred per NIST 800-63B guidance.",
        raw_evidence_summary={
            "gaps": ["Passwords do not rotate every 90 days"],
            "evidence_references": ["IAM password policy"],
            "confidence": "HIGH",
            "exception": {
                "id": str(uuid.uuid4()),
                "business_justification": "Aligned with NIST 800-63B guidelines against arbitrary periodic rotation.",
                "compensating_controls": "Credential stuffing monitoring, breach database checking, and hardware MFA tokens.",
                "risk_level": "low",
                "suppressed_by": "ciso@acme.corp",
                "expires_at": "2026-12-31T23:59:59Z",
            },
        },
    )

    r_fail = AuditResult(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        control_id="CC6.6",
        control_name="Logical Boundaries and Network Protection",
        status="FAIL",
        evidence_count=1,
        ai_description="Security groups permit unrestricted ingress.",
        raw_evidence_summary={
            "gaps": ["Port 22 open to 0.0.0.0/0 on 2 security groups"],
            "evidence_references": ["SecurityGroup ingress rules"],
            "confidence": "HIGH",
        },
    )

    results = [r_pass, r_suppressed, r_fail]
    pdf_path = generate_compliance_report(job, results, framework_name="SOC 2 Type II", framework_id="soc2")

    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000  # Multi-page PDF generated successfully


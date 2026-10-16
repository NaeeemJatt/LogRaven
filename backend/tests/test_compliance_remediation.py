"""Tests for actionable step-by-step compliance remediation guides.

Covers:
- Curated catalog lookups by signal and by control ID.
- Fallback guide synthesis for unmapped controls.
- API route enrichment with structured remediation guides.
- In-memory PDF rendering with remediation commands.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.compliance import routes as compliance_routes
from app.compliance.remediation import RemediationGuide, get_remediation_guide
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.soc2_audit import AuditJob, AuditResult


def test_get_remediation_guide_direct_signal_match():
    guide = get_remediation_guide("s3_public_access_blocked")
    assert guide.control_id == "s3_public_access_blocked"
    assert "Public Access Block" in guide.title
    assert len(guide.console_steps) >= 3
    assert "aws s3control put-public-access-block" in guide.aws_cli_command
    assert "aws_s3_account_public_access_block" in guide.terraform_snippet
    assert "aws s3control get-public-access-block" in guide.verification_command


def test_get_remediation_guide_mapped_control_id():
    guide = get_remediation_guide("CC6.1")
    assert guide.control_id == "CC6.1"
    assert "Root Account" in guide.title or "MFA" in guide.title
    assert "aws iam get-account-summary" in guide.verification_command


def test_get_remediation_guide_referenced_signals():
    guide = get_remediation_guide("custom_sec_group_ctl", signals=["open_security_groups"])
    assert guide.control_id == "custom_sec_group_ctl"
    assert "0.0.0.0/0" in guide.threat_rationale or "ingress" in guide.title.lower()
    assert "aws ec2 revoke-security-group-ingress" in guide.aws_cli_command


def test_get_remediation_guide_fallback():
    guide = get_remediation_guide(
        "CUSTOM.99",
        control_name="Special Hardware Security Module Verification",
        guidance="Ensure CloudHSM cluster has at least two active HSMs in separate AZs.",
    )
    assert guide.control_id == "CUSTOM.99"
    assert "Special Hardware Security Module Verification" in guide.title
    assert "CloudHSM" in guide.threat_rationale
    assert len(guide.console_steps) >= 2
    assert "aws resourcegroupstaggingapi" in guide.aws_cli_command


class _FakeDb:
    def __init__(self):
        self.added = []
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.refresh = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock()


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
        email="devops@acme.corp",
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


def test_get_remediation_endpoint_returns_structured_guides(client):
    c, user, db = client
    audit_id = uuid.uuid4()
    job = AuditJob(
        id=audit_id,
        user_id=user.id,
        company_name="Acme Corp",
        frameworks=["soc2"],
        status="complete",
    )
    r_fail = AuditResult(
        id=uuid.uuid4(),
        audit_job_id=audit_id,
        framework="soc2",
        control_id="CC6.6",
        control_name="Logical Boundaries and Network Protection",
        status="FAIL",
        evidence_count=1,
        ai_description="Open ports detected.",
        raw_evidence_summary={
            "gaps": ["Port 22 open to 0.0.0.0/0"],
            "remediation": "Restrict security group ingress.",
        },
    )

    db.execute.side_effect = [
        _ScalarResult(job),
        _ScalarsResult([r_fail]),
    ]

    r = c.get(f"/api/v1/audit/{audit_id}/remediation")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["control_id"] == "CC6.6"
    assert "remediation_guide" in item
    guide = item["remediation_guide"]
    assert "aws ec2 revoke-security-group-ingress" in guide["aws_cli_command"]
    assert len(guide["console_steps"]) > 0
    assert guide["estimated_time_minutes"] > 0

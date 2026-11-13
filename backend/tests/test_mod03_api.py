"""API integration tests for Module 03: Real-Time IOA & SIEM Engine endpoints."""

import sys
if "ujson" not in sys.modules:
    sys.modules["ujson"] = None

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="secops@lograven.io",
        name="Security Operations Lead",
        password_hash="argon2id$mocked$hash",
        email_verified=True,
    )


@pytest.mark.asyncio
async def test_get_ioa_detection_rules(test_user):
    """Verifies /api/v1/ioa/rules lists all MITRE ATT&CK coverage and rule inventory."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.get("/api/v1/ioa/rules")
        assert res.status_code == 200
        data = res.json()
        assert "tactics_covered" in data
        assert "PRIVILEGE_ESCALATION" in data["tactics_covered"]
        assert "ENUMERATION" in data["tactics_covered"]
        rule_ids = [r["rule_id"] for r in data["active_rules"]]
        assert "IOA-AWS-PRIVESC-004" in rule_ids
        assert "IOA-CLOUD-ENUM-011" in rule_ids

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stream_event_ingestion_and_ocsf_mapping(test_user):
    """Verifies /api/v1/ioa/events/stream normalizes raw CloudTrail event to OCSF v1.2 and extracts priority crawl job."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    payload = {
        "provider": "aws",
        "raw_event": {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "arn": "arn:aws:iam::123456789012:user/admin-dan",
                "accountId": "123456789012",
            },
            "eventTime": "2026-11-13T10:45:00Z",
            "eventSource": "ec2.amazonaws.com",
            "eventName": "AuthorizeSecurityGroupIngress",
            "awsRegion": "us-east-1",
            "sourceIPAddress": "198.51.100.99",
            "requestParameters": {
                "groupId": "sg-998877",
            },
            "readOnly": False,
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/ioa/events/stream", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "PROCESSED"
        ocsf = data["ocsf_event"]
        assert ocsf["provider"] == "aws"
        assert ocsf["event_name"] == "AuthorizeSecurityGroupIngress"
        assert ocsf["read_only"] == 0
        assert "sg-998877" in ocsf["target_resource_urn"]

        # Mutating event must enqueue priority crawl
        assert data["priority_crawl_job"] is not None
        assert data["priority_crawl_job"]["priority"] == "HIGH"
        assert data["priority_crawl_job"]["resource_id"] == "sg-998877"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_retroactive_investigation_endpoint(test_user):
    """Verifies /api/v1/ioa/investigate returns SIEM lookback findings and risk multipliers."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    payload = {
        "finding_id": "IOM-TEST-001",
        "target_resource_urn": "urn:lograven:aws:123456789012:us-east-1:s3:aws_s3_bucket/vault-bucket",
        "base_risk_score": 6.0,
        "lookback_days": 90,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        res = await client.post("/api/v1/ioa/investigate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["finding_id"] == "IOM-TEST-001"
        assert data["lookback_performed"] is True
        assert data["lookback_window_days"] == 90
        assert data["siem_activity_multiplier"] in (1.0, 1.5)
        assert "investigation_summary" in data

    app.dependency_overrides.clear()

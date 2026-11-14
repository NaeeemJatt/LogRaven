"""API integration tests for Module 09: AI-SPM & MCP Governance Engine."""

import sys
if "ujson" not in sys.modules:
    sys.modules["ujson"] = None

import base64
import pickle
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
        email="aispm-sec@lograven.io",
        name="AI Security Engineer",
        password_hash="argon2id$mocked$hash",
        email_verified=True,
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None),
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
        )
    )
    return db


@pytest.mark.asyncio
async def test_aispm_pickle_scan_endpoint_rce_detection(test_user):
    """Tests /api/v1/aispm/scan/pickle safely detects pickled os.system payload."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    class MaliciousPayload:
        def __reduce__(self):
            import os
            return (os.system, ("cat /etc/passwd",))

    payload_bytes = pickle.dumps(MaliciousPayload(), protocol=4)
    payload_b64 = base64.b64encode(payload_bytes).decode("ascii")

    req_body = {
        "filename": "model_weights.pkl",
        "payload_base64": payload_b64,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/aispm/scan/pickle", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_unsafe_deserialization"] is True
    assert data["scan_result"]["finding_code"] == "CRITICAL_PICKLE_RCE"
    assert data["format_evaluation"]["is_safe_format"] is False


@pytest.mark.asyncio
async def test_aispm_mcp_audit_endpoint_shell_tool(test_user, mock_db):
    """Tests /api/v1/aispm/scan/mcp flags unauthenticated public MCP server with execute_bash."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    req_body = {
        "server_urn": "urn:lograven:mcp:us-east-1:123456789012:server/dev-mcp",
        "endpoint_url": "http://198.51.100.22:8000/sse",
        "tools": [
            {
                "name": "execute_bash",
                "description": "Run bash command inside agent container",
            }
        ],
        "auth_enforced": False,
        "network_binding": "0.0.0.0",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/aispm/scan/mcp", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_publicly_exposed"] is True
    assert data["auth_enforced"] is False
    assert data["has_high_risk_tools"] is True
    assert data["overall_severity"] == "CRITICAL"


@pytest.mark.asyncio
async def test_aispm_bedrock_audit_endpoint(test_user, mock_db):
    """Tests /api/v1/aispm/scan/bedrock detects missing guardrail and disabled logging."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    req_body = {
        "endpoint_urn": "arn:aws:bedrock:us-east-1:123456789012:custom-model/test-ai",
        "model_name": "test-ai",
        "guardrail_identifier": None,
        "logging_config": None,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/aispm/scan/bedrock", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["guardrails_enabled"] is False
    assert data["prompt_logging_enabled"] is False
    codes = [f["finding_code"] for f in data["findings"]]
    assert "AI_MISSING_GUARDRAIL" in codes
    assert "AI_LOGGING_DISABLED" in codes


@pytest.mark.asyncio
async def test_aispm_vector_db_endpoint(test_user):
    """Tests /api/v1/aispm/scan/vector-db flags public unauthenticated vector database."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    req_body = {
        "engine": "qdrant",
        "endpoint_url": "http://198.51.100.80:6333",
        "api_key_required": False,
        "is_in_vpc": False,
        "tls_enabled": False,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/aispm/scan/vector-db", json=req_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_public"] is True
    assert data["status"] == "VULNERABLE"

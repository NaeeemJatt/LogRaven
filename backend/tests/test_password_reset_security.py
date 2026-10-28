# LogRaven — Password Reset Security & Anti-Interception Test Suite
#
# PURPOSE:
#   Validates zero-knowledge anti-enumeration, Burp Suite proxy interception defense,
#   HTTP parameter pollution rejection, CRLF header injection mitigation,
#   NIST SP 800-63B password complexity, single-use token lifecycle, and session revocation.

import base64
import json
import os
import time
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from app.dependencies import get_db
from app.limiter import limiter
from app.main import app

limiter.enabled = False
from app.services import account_service
from app.utils import security
from app.utils.crypto_envelope import get_crypto_envelope_manager
from app.utils.password_policy import evaluate_password_policy, validate_password_complexity


def _encrypt_payload_client_side(public_key_pem: str, key_id: str, data: dict) -> dict:
    """Simulates frontend Web Crypto API hybrid envelope encryption."""
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    aes_key = AESGCM.generate_key(256)

    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    payload = {
        **data,
        "timestamp": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }
    plaintext_bytes = json.dumps(payload).encode("utf-8")

    iv = os.urandom(12)
    aesgcm = AESGCM(aes_key)
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext_bytes, None)

    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]

    return {
        "key_id": key_id,
        "encrypted_key": base64.b64encode(encrypted_key).decode("utf-8"),
        "iv": base64.b64encode(iv).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
        "tag": base64.b64encode(tag).decode("utf-8"),
    }


def _mock_db(user=None):
    result = SimpleNamespace(scalar_one_or_none=lambda: user)
    db = SimpleNamespace(
        execute=AsyncMock(return_value=result),
        add=lambda *_: None,
        commit=AsyncMock(),
    )
    return db


@pytest.fixture(autouse=True)
def clean_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_anti_enumeration_parity():
    """Ensure existing and non-existing emails return identical status code and message."""
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="realuser@lograven.io",
        password_hash=security.hash_password("SuperSecret123!@#"),
        tier="pro",
        email_verified=True,
    )

    # 1. Existing email
    app.dependency_overrides[get_db] = lambda: _mock_db(user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.post("/auth/password/forgot", json={"email": "realuser@lograven.io"})
        assert resp1.status_code == 202
        body1 = resp1.json()
        assert body1["ok"] is True
        assert "password reset link has been dispatched" in body1["message"]

    # 2. Non-existing email
    app.dependency_overrides[get_db] = lambda: _mock_db(None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp2 = await client.post("/auth/password/forgot", json={"email": "ghostuser@lograven.io"})
        assert resp2.status_code == 202
        body2 = resp2.json()
        assert body2["ok"] is True
        assert body2["message"] == body1["message"]


@pytest.mark.asyncio
async def test_parameter_pollution_and_multi_recipient_rejected():
    """Attackers injecting arrays, duplicate parameters, or delimiter lists must be blocked with 422."""
    app.dependency_overrides[get_db] = lambda: _mock_db(None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Array parameter injection
        resp = await client.post("/auth/password/forgot", json={"email": ["alice@target.com", "hacker@evil.com"]})
        assert resp.status_code == 422

        # 2. Comma-separated multi-recipient injection
        resp = await client.post("/auth/password/forgot", json={"email": "alice@target.com,hacker@evil.com"})
        assert resp.status_code == 422

        # 3. Semicolon list injection
        resp = await client.post("/auth/password/forgot", json={"email": "alice@target.com;hacker@evil.com"})
        assert resp.status_code == 422

        # 4. CRLF / SMTP header injection
        resp = await client.post("/auth/password/forgot", json={"email": "alice@target.com\r\nBcc:hacker@evil.com"})
        assert resp.status_code == 422

        # 5. Extra unpermitted keys (parameter pollution)
        resp = await client.post("/auth/password/forgot", json={"email": "alice@target.com", "secondary_email": "hacker@evil.com"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_crypto_envelope_forgot_password_flow():
    """Burp Suite interception defense: request body is 100% opaque ciphertext."""
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="secure_operator@lograven.io",
        password_hash=security.hash_password("ComplexP@ssw0rd2026!"),
        tier="team",
        email_verified=True,
    )
    app.dependency_overrides[get_db] = lambda: _mock_db(user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch public key
        pk_resp = await client.get("/auth/crypto/public-key")
        assert pk_resp.status_code == 200
        pk_info = pk_resp.json()
        assert "public_key" in pk_info
        assert pk_info["algorithm"] == "RSA-OAEP-256"

        # 2. Client-side encrypt payload
        envelope = _encrypt_payload_client_side(
            pk_info["public_key"],
            pk_info["key_id"],
            {"email": "secure_operator@lograven.io"},
        )

        # 3. Submit envelope (over wire, zero cleartext email)
        resp = await client.post("/auth/password/forgot", json={"envelope": envelope})
        assert resp.status_code == 202
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_crypto_envelope_tampering_and_replay_rejection():
    """Tampering with ciphertext bytes in Burp Suite or replaying nonces must fail."""
    app.dependency_overrides[get_db] = lambda: _mock_db(None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        pk_resp = await client.get("/auth/crypto/public-key")
        pk_info = pk_resp.json()

        envelope = _encrypt_payload_client_side(
            pk_info["public_key"],
            pk_info["key_id"],
            {"email": "tamper_test@lograven.io"},
        )

        # 1. Tamper 1 byte of tag
        tampered_tag = bytearray(base64.b64decode(envelope["tag"]))
        tampered_tag[0] ^= 0xFF
        bad_envelope = {**envelope, "tag": base64.b64encode(tampered_tag).decode("utf-8")}

        resp = await client.post("/auth/password/forgot", json={"envelope": bad_envelope})
        assert resp.status_code == 400
        assert "tampered" in resp.json()["detail"].lower() or "failed" in resp.json()["detail"].lower()

        # 2. Replay attack: submit same envelope twice
        resp_first = await client.post("/auth/password/forgot", json={"envelope": envelope})
        assert resp_first.status_code == 202

        resp_replay = await client.post("/auth/password/forgot", json={"envelope": envelope})
        assert resp_replay.status_code == 400
        assert "replay" in resp_replay.json()["detail"].lower()


@pytest.mark.asyncio
async def test_pre_flight_verification_endpoint():
    """Pre-flight verification checks token status without consuming it."""
    user_id = str(uuid.uuid4())
    pw_hash = security.hash_password("OldPassword123!@#")
    user = SimpleNamespace(
        id=uuid.UUID(user_id),
        email="operator_preflight@lograven.io",
        password_hash=pw_hash,
        tier="pro",
        email_verified=True,
    )
    token = security.create_password_reset_token(user_id, pw_hash)

    app.dependency_overrides[get_db] = lambda: _mock_db(user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid token
        resp = await client.get(f"/auth/password/reset/verify?token={token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert "o***t@lograven.io" in data["email_masked"]

        # Expired or invalid token
        bad_resp = await client.get("/auth/password/reset/verify?token=invalid.token.123")
        assert bad_resp.status_code == 400


def test_nist_password_complexity_unit():
    """Validates policy rules individually: length, uppercase, lowercase, numbers, symbols, context."""
    # Too short (<12)
    eval1 = evaluate_password_policy("Short1!", email="alice@test.com")
    assert eval1["min_length"] is False
    assert eval1["valid"] is False

    # Missing symbol
    eval2 = evaluate_password_policy("NoSymbolsHere1234", email="alice@test.com")
    assert eval2["special"] is False
    assert eval2["valid"] is False

    # Email username contained in password
    eval3 = evaluate_password_policy("alice_P@ssw0rd2026!", email="alice@test.com")
    assert eval3["context_safe"] is False
    assert eval3["valid"] is False

    # Common breached password
    eval4 = evaluate_password_policy("password12345", email="alice@test.com")
    assert eval4["not_breached"] is False
    assert eval4["valid"] is False

    # Strong compliant password
    eval5 = evaluate_password_policy("StrongCompliantP@ss2026!", email="alice@test.com")
    assert eval5["valid"] is True


@pytest.mark.asyncio
async def test_full_reset_and_single_use_token_invalidation():
    """Performs reset and verifies token cannot be reused once password hash changes."""
    user_id = str(uuid.uuid4())
    initial_hash = security.hash_password("InitialPassword123!")
    user = SimpleNamespace(
        id=uuid.UUID(user_id),
        email="reset_target@lograven.io",
        password_hash=initial_hash,
        tier="pro",
        email_verified=True,
    )
    token = security.create_password_reset_token(user_id, initial_hash)

    app.dependency_overrides[get_db] = lambda: _mock_db(user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Reset password
        resp = await client.post(
            "/auth/password/reset",
            json={"token": token, "new_password": "NewStrongP@ssw0rd2026!"},
        )
        assert resp.status_code == 204
        # User hash updated
        assert user.password_hash != initial_hash

        # 2. Token cannot be reused (fingerprint invalidation)
        reuse_resp = await client.post(
            "/auth/password/reset",
            json={"token": token, "new_password": "AnotherNewP@ssw0rd2026!"},
        )
        assert reuse_resp.status_code == 400
        assert "already been used" in reuse_resp.json()["detail"].lower()

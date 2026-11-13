"""Security test suite for Confused Deputy prevention and ExternalId cryptography (TC-MOD1-004)."""

import logging
from unittest.mock import MagicMock
import pytest
from botocore.exceptions import ClientError

from services.mod01_onboarding.internal.crypto import (
    generate_external_id,
    encrypt_external_id,
    decrypt_external_id,
)
from services.mod01_onboarding.internal.sts_broker.aws_sts import STSAssumeRoleBroker
from services.mod01_onboarding.internal.sts_broker.token_cache import TokenCache


def test_crypto_external_id_generation_and_encryption():
    """Verify 128-bit external ID format and AES-256-GCM encryption round-trip."""
    ext_1 = generate_external_id()
    ext_2 = generate_external_id()

    assert ext_1.startswith("lr-ext-")
    assert ext_2.startswith("lr-ext-")
    assert ext_1 != ext_2
    assert len(ext_1) == 7 + 32  # lr-ext- + 32 hex chars

    # Encrypt
    encrypted = encrypt_external_id(ext_1)
    assert isinstance(encrypted, bytes)
    assert len(encrypted) >= 12 + 16 # 12-byte nonce + 16-byte tag minimum

    # Decrypt
    decrypted = decrypt_external_id(encrypted)
    assert decrypted == ext_1


def test_crypto_corrupted_ciphertext_rejected():
    """Verify corrupted ciphertext fails authentication in AES-256-GCM."""
    ext = generate_external_id()
    encrypted = bytearray(encrypt_external_id(ext))
    # Flip bit in ciphertext
    encrypted[-1] ^= 0xFF

    with pytest.raises(Exception):
        decrypt_external_id(bytes(encrypted))


@pytest.mark.asyncio
async def test_tc_mod1_004_confused_deputy_blocked(caplog):
    """TC-MOD1-004: Confused-Deputy Simulation.
    
    Tenant B attempts to register/assume Tenant A's role_arn using Tenant B's ExternalId.
    AWS STS raises AccessDenied; broker logs SEC_CONFUSED_DEPUTY_BLOCKED.
    """
    mock_sts = MagicMock()
    error_response = {
        "Error": {
            "Code": "AccessDenied",
            "Message": "User: arn:aws:iam::112233445566:root is not authorized to perform: sts:AssumeRole on resource: arn:aws:iam::tenant-a:role/LogRavenCSPMReader",
        }
    }
    mock_sts.assume_role.side_effect = ClientError(error_response, "AssumeRole")

    broker = STSAssumeRoleBroker(cache=TokenCache(), sts_client=mock_sts)

    tenant_b_id = "tenant-b-attacker"
    tenant_a_role = "arn:aws:iam::tenant-a:role/LogRavenCSPMReader"
    tenant_b_ext_id = "lr-ext-tenant-b-secret-external-id"

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ClientError) as exc_info:
            await broker.get_credentials(
                tenant_id=tenant_b_id,
                account_id="account-attacker",
                role_arn=tenant_a_role,
                external_id=tenant_b_ext_id,
            )

        assert exc_info.value.response["Error"]["Code"] == "AccessDenied"
        assert "SEC_CONFUSED_DEPUTY_BLOCKED" in caplog.text


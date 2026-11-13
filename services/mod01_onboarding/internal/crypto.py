"""Cryptographic utilities for Module 01: Multi-Cloud Onboarding & Trust Broker.

Implements:
- 128-bit cryptographic ExternalId generation (FR-MOD1-01)
- AES-256-GCM authenticated encryption/decryption of external IDs
"""

import hashlib
import os
import secrets
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Default salt / domain separator for key derivation
_KDF_SALT = b"LogRaven-Module01-TrustBroker-v1"


def get_master_encryption_key() -> bytes:
    """Derive 32-byte AES-256 key from environment variable or application secret."""
    raw_key = os.environ.get("LOGRAVEN_ENCRYPTION_KEY") or os.environ.get("SECRET_KEY") or "lograven-default-dev-secret-key-32b!"
    # Ensure 32 bytes via SHA-256
    return hashlib.sha256(raw_key.encode("utf-8") + _KDF_SALT).digest()


def generate_external_id() -> str:
    """Generate a unique 128-bit cryptographic token (lr-ext-{32_hex_chars})."""
    return f"lr-ext-{secrets.token_hex(16)}"


def encrypt_external_id(external_id: str, key: Optional[bytes] = None) -> bytes:
    """Encrypt external ID using AES-256-GCM.
    
    Returns 12-byte nonce prepended to the ciphertext + 16-byte authentication tag.
    """
    key_bytes = key or get_master_encryption_key()
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, external_id.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_external_id(encrypted_blob: bytes, key: Optional[bytes] = None) -> str:
    """Decrypt external ID using AES-256-GCM."""
    if len(encrypted_blob) < 28: # 12 nonce + 16 tag minimum
        raise ValueError("Encrypted blob is too short to be valid AES-256-GCM payload")
    
    key_bytes = key or get_master_encryption_key()
    aesgcm = AESGCM(key_bytes)
    nonce = encrypted_blob[:12]
    ciphertext = encrypted_blob[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


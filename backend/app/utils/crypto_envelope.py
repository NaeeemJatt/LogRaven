# LogRaven — Cryptographic Envelope Service
#
# PURPOSE:
#   Provides asymmetric (RSA-OAEP 2048-bit) and symmetric (AES-256-GCM)
#   hybrid envelope encryption for zero-plaintext transport security.
#   Protects sensitive requests (e.g., password reset, forgot password)
#   against inspection by local proxies (Burp Suite, OWASP ZAP) or MITM.
#
# INVARIANTS:
#   - Ephemeral AES-256-GCM symmetric key encrypted with server RSA-OAEP public key.
#   - GCM 128-bit authentication tag verification ensures tamper detection.
#   - Millisecond timestamps reject payloads older than 60 seconds (anti-replay).
#   - Random UUID nonces cached in memory / Redis to reject replay attacks.

from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Key metadata
KEY_ID = "lograven-crypto-v1"
MAX_DRIFT_SECONDS = 60.0

# In-memory nonce cache with TTL (secondary layer behind Redis)
_SEEN_NONCES: dict[str, float] = {}


class EncryptedEnvelope(BaseModel):
    """Encrypted envelope model sent over the wire."""

    key_id: str = Field(..., description="Target server public key identifier")
    encrypted_key: str = Field(..., description="Base64-encoded RSA-OAEP encrypted AES key")
    iv: str = Field(..., description="Base64-encoded 12-byte AES-GCM initialization vector")
    ciphertext: str = Field(..., description="Base64-encoded AES-GCM ciphertext")
    tag: str = Field(..., description="Base64-encoded 16-byte AES-GCM authentication tag")

    model_config = ConfigDict(extra="forbid", strict=True)


class CryptoEnvelopeManager:
    """Manages the server RSA key pair and hybrid envelope decryption."""

    def __init__(self, key_dir: Optional[str] = None):
        self._key_dir = Path(key_dir or "backend/local/keys")
        self._private_key: rsa.RSAPrivateKey | None = None
        self._public_key_pem: str | None = None
        self._initialize_keys()

    def _initialize_keys(self) -> None:
        """Loads existing key pair from disk or generates a fresh 2048-bit RSA pair."""
        try:
            self._key_dir.mkdir(parents=True, exist_ok=True)
            priv_path = self._key_dir / "envelope_rsa_private.pem"
            pub_path = self._key_dir / "envelope_rsa_public.pem"

            if priv_path.exists() and pub_path.exists():
                with open(priv_path, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(f.read(), password=None)
                with open(pub_path, "r", encoding="utf-8") as f:
                    self._public_key_pem = f.read()
                logger.info("[crypto-envelope] Loaded server key pair from disk | key_id=%s", KEY_ID)
                return
        except Exception as exc:
            logger.warning("[crypto-envelope] Could not load keys from disk: %s. Generating in-memory pair.", exc)

        # Generate fresh 2048-bit key
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        pub = self._private_key.public_key()
        self._public_key_pem = pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        # Attempt to save to disk if possible
        try:
            priv_pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            priv_path = self._key_dir / "envelope_rsa_private.pem"
            pub_path = self._key_dir / "envelope_rsa_public.pem"
            with open(priv_path, "wb") as f:
                f.write(priv_pem)
            with open(pub_path, "w", encoding="utf-8") as f:
                f.write(self._public_key_pem)
            logger.info("[crypto-envelope] Saved fresh RSA key pair to %s", self._key_dir)
        except Exception:
            pass

    @property
    def key_id(self) -> str:
        return KEY_ID

    @property
    def public_key_pem(self) -> str:
        if not self._public_key_pem:
            raise RuntimeError("Crypto envelope public key not initialized")
        return self._public_key_pem

    def get_public_key_info(self) -> dict[str, str]:
        return {
            "key_id": self.key_id,
            "algorithm": "RSA-OAEP-256",
            "public_key": self.public_key_pem,
        }

    def decrypt_envelope(self, envelope: EncryptedEnvelope) -> dict[str, Any]:
        """
        Decrypts an encrypted envelope:
        1. Verifies key_id matches current server key.
        2. Decrypts AES key via RSA-OAEP with SHA-256.
        3. Decrypts AES-GCM ciphertext with IV and verifies authentication tag.
        4. Validates embedded timestamp (max 60 seconds clock drift).
        5. Validates and caches nonce to prevent replay attacks.
        """
        if envelope.key_id != self.key_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or retired key_id: {envelope.key_id}. Expected {self.key_id}.",
            )

        if not self._private_key:
            raise HTTPException(status_code=500, detail="Server encryption key unavailable")

        # 1. Base64 decode fields
        try:
            encrypted_key_bytes = base64.b64decode(envelope.encrypted_key)
            iv_bytes = base64.b64decode(envelope.iv)
            ciphertext_bytes = base64.b64decode(envelope.ciphertext)
            tag_bytes = base64.b64decode(envelope.tag)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed base64 in encrypted envelope payload",
            ) from exc

        if len(iv_bytes) != 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid AES-GCM IV length; expected exactly 12 bytes.",
            )

        if len(tag_bytes) != 16:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid AES-GCM tag length; expected exactly 16 bytes.",
            )

        # 2. Decrypt AES key with RSA-OAEP
        try:
            aes_key = self._private_key.decrypt(
                encrypted_key_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decrypt symmetric key envelope. Key tampering or invalid format.",
            ) from exc

        # 3. Decrypt payload via AES-256-GCM
        try:
            aesgcm = AESGCM(aes_key)
            # AESGCM.decrypt expects ciphertext + tag combined
            plaintext_bytes = aesgcm.decrypt(iv_bytes, ciphertext_bytes + tag_bytes, None)
        except InvalidTag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ciphertext authentication tag verification failed. Payload was tampered with or corrupted.",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload decryption failed",
            ) from exc

        # 4. Parse JSON payload
        try:
            payload: dict[str, Any] = json.loads(plaintext_bytes.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decrypted payload is not valid JSON",
            ) from exc

        # 5. Timestamp validation (<60 seconds clock drift)
        ts = payload.get("timestamp")
        if ts is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decrypted payload missing required security timestamp",
            )

        # Handle either ms epoch or seconds epoch
        now_ms = time.time() * 1000.0
        ts_ms = float(ts) if float(ts) > 1e11 else float(ts) * 1000.0
        drift_seconds = abs(now_ms - ts_ms) / 1000.0

        if drift_seconds > MAX_DRIFT_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security timestamp expired or out of sync ({drift_seconds:.1f}s drift > {MAX_DRIFT_SECONDS}s allowed).",
            )

        # 6. Nonce replay prevention
        nonce = payload.get("nonce")
        if not nonce or not isinstance(nonce, str) or len(nonce) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decrypted payload missing valid high-entropy nonce",
            )

        now = time.time()
        # Clean expired nonces
        expired = [n for n, exp in _SEEN_NONCES.items() if exp < now]
        for n in expired:
            _SEEN_NONCES.pop(n, None)

        if nonce in _SEEN_NONCES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Replay attack detected: cryptographic nonce has already been consumed.",
            )

        _SEEN_NONCES[nonce] = now + 120.0  # 2 minute retention

        return payload


# Global singleton instance
envelope_manager = CryptoEnvelopeManager()


def get_crypto_envelope_manager() -> CryptoEnvelopeManager:
    return envelope_manager

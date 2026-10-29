# LogRaven — User Pydantic Schemas
#
# PURPOSE:
#   Defines the shapes of data coming IN (requests) and going OUT (responses).
#   Completely separate from SQLAlchemy models — never expose ORM objects directly.
#
# SECURITY:
#   - Extra fields are strictly forbidden (`extra="forbid"`).
#   - `StrictSingleEmail` custom type permanently prevents HTTP Parameter Pollution (HPP),
#     multi-recipient injection (arrays, commas, semicolons), and SMTP CRLF injection.
#   - Supports hybrid encrypted payloads for zero-plaintext wire transmission.

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# Strict single-email validation regex and rules
# Forbids commas, semicolons, whitespace, quotes, angle brackets, and CRLF
FORBIDDEN_CHARS_PATTERN = re.compile(r"""[,;\s"\'<>\r\n\t]""")


def validate_strict_single_email(value: str) -> str:
    """Ensures value contains exactly one clean RFC-compliant email address without delimiters or whitespace."""
    if not isinstance(value, str):
        raise ValueError("Email must be a string")

    stripped = value.strip()
    if not stripped:
        raise ValueError("Email cannot be empty")

    if FORBIDDEN_CHARS_PATTERN.search(stripped):
        raise ValueError("Email must contain exactly one recipient without commas, semicolons, spaces, quotes, or newlines")

    if stripped.count("@") != 1:
        raise ValueError("Email must contain exactly one '@' character")

    local_part, domain = stripped.split("@")
    if not local_part or not domain:
        raise ValueError("Email local-part and domain cannot be empty")

    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Email domain must contain valid dot-separated host components")

    # Additional check: simple sanity regex
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", stripped):
        raise ValueError("Email format is invalid")

    return stripped.lower()


StrictSingleEmail = Annotated[str, Field(..., description="Single valid email recipient without delimiters")]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)

    model_config = ConfigDict(extra="forbid")


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    id: UUID
    email: str
    tier: str
    email_verified: bool = False
    name: Optional[str] = None
    timezone: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., max_length=128)

    model_config = ConfigDict(extra="forbid")


class VerifyEmailRequest(BaseModel):
    token: str

    model_config = ConfigDict(extra="forbid")


class EncryptedEnvelopeRequest(BaseModel):
    """Encrypted envelope model for zero-plaintext transport."""

    key_id: str = Field(..., description="Target server public key identifier")
    encrypted_key: str = Field(..., description="Base64-encoded RSA-OAEP encrypted AES key")
    iv: str = Field(..., description="Base64-encoded 12-byte AES-GCM initialization vector")
    ciphertext: str = Field(..., description="Base64-encoded AES-GCM ciphertext")
    tag: str = Field(..., description="Base64-encoded 16-byte AES-GCM authentication tag")

    model_config = ConfigDict(extra="forbid", strict=True)


class ForgotPasswordRequest(BaseModel):
    """
    Accepts either a strict plain email OR an encrypted envelope.
    Extra fields are strictly forbidden to prevent parameter pollution.
    """

    email: Optional[str] = None
    envelope: Optional[EncryptedEnvelopeRequest] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_strict_single_email(v)
        return None


class ResetPasswordRequest(BaseModel):
    """
    Accepts either cleartext token/password OR an encrypted envelope.
    Extra fields are strictly forbidden.
    """

    token: Optional[str] = None
    new_password: Optional[str] = None
    envelope: Optional[EncryptedEnvelopeRequest] = None

    model_config = ConfigDict(extra="forbid")


class ResetVerifyResponse(BaseModel):
    """Pre-flight verification result for reset password links."""

    valid: bool
    email_masked: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None


class DeleteAccountRequest(BaseModel):
    password: str

    model_config = ConfigDict(extra="forbid")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class AuthSessionResponse(BaseModel):
    """HTTP shape after login/register/refresh; tokens omitted unless INCLUDE_TOKENS_IN_AUTH_JSON."""

    token_type: str = "bearer"
    access_token: str | None = None
    refresh_token: str | None = None
    user: UserResponse | None = None

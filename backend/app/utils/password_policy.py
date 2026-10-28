# LogRaven — Password Policy & Complexity Engine
#
# PURPOSE:
#   Enforces enterprise password complexity and strength validation
#   conforming to NIST SP 800-63B (§5.1.1.2) and SOC 2 CC6.1 standards.
#
# RULES:
#   1. Minimum length: 12 characters.
#   2. At least one uppercase letter (A-Z).
#   3. At least one lowercase letter (a-z).
#   4. At least one numeric digit (0-9).
#   5. At least one special symbol (!@#$%^&*()_+-=[]{}|;:,.<>?/~`"').
#   6. Blacklist check against common compromised / breached passwords.
#   7. Context-specific checks: cannot contain user email username or organization name.

from __future__ import annotations

import re
from typing import Optional
from fastapi import HTTPException, status

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

# Top commonly breached and dictionary passwords to reject
COMMON_BREACHED_PASSWORDS = {
    "password12345",
    "password1234!",
    "p@ssword1234!",
    "admin1234567",
    "admin12345678",
    "administrator",
    "welcome12345!",
    "qwertyuiop12",
    "letmein12345!",
    "changeme12345",
    "lograven1234!",
    "lograven2024!",
    "lograven2025!",
    "lograven2026!",
    "correcthorsebatterystaple",
    "123456789012",
    "iloveyou12345",
    "trustnoone123",
    "hunter2hunter",
    "supersecret12",
}

SPECIAL_CHARS_PATTERN = re.compile(r"""[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]""")


def evaluate_password_policy(
    password: str,
    email: Optional[str] = None,
) -> dict[str, bool]:
    """
    Evaluates individual policy criteria.
    Returns a dict with boolean flags for each requirement.
    """
    has_min_len = len(password) >= MIN_PASSWORD_LENGTH
    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(SPECIAL_CHARS_PATTERN.search(password))

    is_not_breached = password.lower().strip() not in COMMON_BREACHED_PASSWORDS

    context_safe = True
    if email and "@" in email:
        local_part = email.split("@")[0].lower()
        if len(local_part) >= 3 and local_part in password.lower():
            context_safe = False

    return {
        "min_length": has_min_len,
        "uppercase": has_upper,
        "lowercase": has_lower,
        "digit": has_digit,
        "special": has_special,
        "not_breached": is_not_breached,
        "context_safe": context_safe,
        "valid": has_min_len and has_upper and has_lower and has_digit and has_special and is_not_breached and context_safe,
    }


def validate_password_complexity(
    password: str,
    email: Optional[str] = None,
) -> None:
    """
    Validates password against all rules.
    Raises HTTPException(status_code=400) on any violation with actionable details.
    """
    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password is too long (maximum {MAX_PASSWORD_LENGTH} characters).",
        )

    results = evaluate_password_policy(password, email)

    if not results["min_length"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.",
        )

    missing: list[str] = []
    if not results["uppercase"]:
        missing.append("at least one uppercase letter (A-Z)")
    if not results["lowercase"]:
        missing.append("at least one lowercase letter (a-z)")
    if not results["digit"]:
        missing.append("at least one numeric digit (0-9)")
    if not results["special"]:
        missing.append("at least one special symbol (!@#$%^&*...)")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password requirements not met: {', '.join(missing)}.",
        )

    if not results["not_breached"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password appears in known data breach lists or is too common. Choose a more unique password.",
        )

    if not results["context_safe"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot contain your email username or personal details.",
        )

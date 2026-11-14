"""Pattern Matcher & Redaction Engine for Secret & Plaintext Key Detection (FR-MOD4-05, TC-MOD4-003)."""

import hashlib
import re
from typing import Any, Dict, List

from services.mod04_disk_scanner.internal.secret_scanner.entropy_analyzer import is_high_entropy

# Secret identification patterns
SECRET_PATTERNS = [
    {
        "rule_id": "SECRET_AWS_KEY",
        "name": "AWS Access Key ID",
        "regex": r"(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)",
        "group": 1,
    },
    {
        "rule_id": "SECRET_PRIVATE_KEY",
        "name": "Unencrypted Private Key",
        "regex": r"(-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----)",
        "group": 1,
    },
    {
        "rule_id": "SECRET_GITHUB_TOKEN",
        "name": "GitHub Personal Access Token",
        "regex": r"(gh[pousr]_[A-Za-z0-9_]{36,255})",
        "group": 1,
    },
    {
        "rule_id": "SECRET_GENERIC_API_KEY",
        "name": "Generic High-Entropy API Token",
        "regex": r'(?:api[_-]?key|secret|token|password)\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{24,120})["\']?',
        "group": 1,
        "check_entropy": True,
    },
]


def mask_secret(secret_val: str) -> str:
    """Masks secret so plaintext is never exposed or logged (TC-MOD4-003).
    
    Preserves first 4 characters and last 4 characters, replacing the middle with asterisks.
    """
    clean = secret_val.strip()
    if len(clean) <= 8:
        return "********"

    prefix = clean[:4]
    suffix = clean[-4:]
    masked_middle = "*" * (len(clean) - 8)
    return f"{prefix}{masked_middle}{suffix}"


def fingerprint_secret(secret_val: str) -> str:
    """Generates cryptographic SHA-256 fingerprint of the secret."""
    return hashlib.sha256(secret_val.strip().encode("utf-8")).hexdigest()[:16]


class SecretScanner:
    """Scans filesystem paths and file contents for plaintext credentials and private keys."""

    @staticmethod
    def scan_content(file_path: str, content: str) -> List[Dict[str, Any]]:
        """Scans text content for credentials and returns masked findings."""
        findings = []

        for rule in SECRET_PATTERNS:
            regex = rule["regex"]
            group_idx = rule.get("group", 0)

            for match in re.finditer(regex, content):
                raw_secret = match.group(group_idx).strip()

                if rule.get("check_entropy") and not is_high_entropy(raw_secret, min_length=20):
                    continue

                masked = mask_secret(raw_secret)
                fingerprint = fingerprint_secret(raw_secret)

                findings.append({
                    "rule_id": rule["rule_id"],
                    "name": rule["name"],
                    "file_path": file_path,
                    "masked_value": masked,
                    "fingerprint": fingerprint,
                    "severity": "CRITICAL",
                })

        return findings


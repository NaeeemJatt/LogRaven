"""Secrets, Cloud Credentials & Token Classifier (FR-MOD8-02, TC-MOD8-002).

Detects AWS keys, GitHub tokens, Slack tokens, JWTs, and RSA/OpenSSH private keys.
"""

import re
from typing import Any, Dict, List

AWS_ACCESS_KEY_REGEX = re.compile(r"\b(AKIA[0-9A-Z]{16})\b")
PRIVATE_KEY_REGEX = re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")
GITHUB_TOKEN_REGEX = re.compile(r"\b(gh[pousr]_[0-9a-zA-Z]{36})\b")
SLACK_TOKEN_REGEX = re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b")
JWT_REGEX = re.compile(r"\b(eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})\b")


class SecretClassifier:
    """Classifies hardcoded secrets and tokens with zero raw plaintext storage."""

    @classmethod
    def scan_text(cls, text: str) -> List[Dict[str, Any]]:
        findings = []

        # 1. AWS Access Keys
        for m in AWS_ACCESS_KEY_REGEX.finditer(text):
            findings.append({
                "category": "SECRET",
                "detector_name": "AWS_ACCESS_KEY_ID",
                "confidence": "HIGH",
                "byte_offset": m.start(),
            })

        # 2. Private Keys
        for m in PRIVATE_KEY_REGEX.finditer(text):
            findings.append({
                "category": "SECRET",
                "detector_name": "ASYMMETRIC_PRIVATE_KEY",
                "confidence": "HIGH",
                "byte_offset": m.start(),
            })

        # 3. GitHub Tokens
        for m in GITHUB_TOKEN_REGEX.finditer(text):
            findings.append({
                "category": "SECRET",
                "detector_name": "GITHUB_PERSONAL_ACCESS_TOKEN",
                "confidence": "HIGH",
                "byte_offset": m.start(),
            })

        # 4. Slack Tokens
        for m in SLACK_TOKEN_REGEX.finditer(text):
            findings.append({
                "category": "SECRET",
                "detector_name": "SLACK_API_TOKEN",
                "confidence": "HIGH",
                "byte_offset": m.start(),
            })

        # 5. JWTs
        for m in JWT_REGEX.finditer(text):
            findings.append({
                "category": "SECRET",
                "detector_name": "JSON_WEB_TOKEN",
                "confidence": "MEDIUM",
                "byte_offset": m.start(),
            })

        return findings

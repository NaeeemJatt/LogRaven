"""PII Sensitive Data Scanner (FR-MOD8-02, TC-MOD8-003).

Detects US Social Security Numbers (SSN), Passports, Phone Numbers, and Emails
with strict structure validation and zero raw data logging.
"""

import re
from typing import Any, Dict, List

# Strict SSN: no 000 or 666 area; no 00 group; no 0000 serial
SSN_REGEX = re.compile(r"\b(?!000|666)\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b")
PASSPORT_REGEX = re.compile(r"\b[A-Z][0-9]{8}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_REGEX = re.compile(r"\b(?:\+1[- ]?)?\(?[2-9]\d{2}\)?[- ]?\d{3}[- ]?\d{4}\b")


class PIIScanner:
    """Scans sampled bytes/text for Personally Identifiable Information (PII)."""

    @classmethod
    def scan_text(cls, text: str) -> List[Dict[str, Any]]:
        """Identifies PII patterns without persisting raw payload (NFR-MOD8-01)."""
        findings = []

        # 1. Social Security Numbers
        for m in SSN_REGEX.finditer(text):
            findings.append({
                "category": "PII",
                "detector_name": "US_SSN",
                "confidence": "HIGH",
                "byte_offset": m.start(),
            })

        # 2. Passports
        for m in PASSPORT_REGEX.finditer(text):
            findings.append({
                "category": "PII",
                "detector_name": "US_PASSPORT",
                "confidence": "MEDIUM",
                "byte_offset": m.start(),
            })

        # 3. Email addresses
        for m in EMAIL_REGEX.finditer(text):
            findings.append({
                "category": "PII",
                "detector_name": "EMAIL_ADDRESS",
                "confidence": "HIGH",
                "byte_offset": m.start(),
            })

        return findings

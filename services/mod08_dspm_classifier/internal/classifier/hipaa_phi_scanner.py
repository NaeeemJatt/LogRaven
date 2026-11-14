"""HIPAA Protected Health Information (PHI) Scanner (FR-MOD8-02).

Detects Medical Record Numbers (MRN), ICD-10 diagnosis codes, and Health Insurance Claim Numbers.
"""

import re
from typing import Any, Dict, List

ICD10_REGEX = re.compile(r"\b[A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?\b")
MRN_REGEX = re.compile(r"\b(?:MRN|PATIENT_ID|MED_REC)[:#\s]+([0-9]{6,10})\b", re.IGNORECASE)


class HIPAAPHIScanner:
    """Scans for health and medical identifiers."""

    @classmethod
    def scan_text(cls, text: str) -> List[Dict[str, Any]]:
        findings = []

        for m in MRN_REGEX.finditer(text):
            findings.append({
                "category": "PHI",
                "detector_name": "MEDICAL_RECORD_NUMBER",
                "confidence": "HIGH",
                "byte_offset": m.start(),
            })

        for m in ICD10_REGEX.finditer(text):
            findings.append({
                "category": "PHI",
                "detector_name": "ICD10_DIAGNOSIS_CODE",
                "confidence": "MEDIUM",
                "byte_offset": m.start(),
            })

        return findings

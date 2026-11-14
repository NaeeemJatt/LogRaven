"""Credit Card Luhn Algorithm Mod-10 Validator (FR-MOD8-02, TC-MOD8-001).

Validates candidate credit card strings using the ISO/IEC 7812 Luhn checksum formula,
eliminating false positives from random 13-19 digit numerical strings.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# Card patterns (13 to 19 digits, optionally separated by dashes or spaces)
CARD_CANDIDATE_REGEX = re.compile(
    r"\b(?:\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}|\d{4}[ -]?\d{6}[ -]?\d{5}|\d{13,19})\b"
)


class LuhnValidator:
    """Validates credit card numbers with strict Luhn mod-10 checksum."""

    @staticmethod
    def is_luhn_valid(card_number: str) -> bool:
        """Executes Luhn mod-10 algorithm on a sanitized digit string (TC-MOD8-001)."""
        digits = [int(c) for c in card_number if c.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False

        # Double every second digit from right to left
        checksum = 0
        reverse_digits = digits[::-1]

        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = digit * 2
                if doubled > 9:
                    doubled -= 9
                checksum += doubled
            else:
                checksum += digit

        return checksum % 10 == 0

    @staticmethod
    def detect_brand(digits: str) -> str:
        """Determines payment card brand from IIN/BIN prefix."""
        if digits.startswith("4"):
            return "CREDIT_CARD_VISA"
        elif digits.startswith(("51", "52", "53", "54", "55")) or (
            len(digits) >= 4 and 2221 <= int(digits[:4]) <= 2720
        ):
            return "CREDIT_CARD_MASTERCARD"
        elif digits.startswith(("34", "37")):
            return "CREDIT_CARD_AMEX"
        elif digits.startswith(("6011", "65")) or (
            len(digits) >= 3 and 644 <= int(digits[:3]) <= 649
        ):
            return "CREDIT_CARD_DISCOVER"
        return "CREDIT_CARD_GENERIC"

    @classmethod
    def scan_text(cls, text: str) -> List[Dict[str, Any]]:
        """Scans text for credit card numbers, validates with Luhn, and yields masked findings."""
        matches = []
        for match in CARD_CANDIDATE_REGEX.finditer(text):
            raw_candidate = match.group(0)
            digits = "".join(c for c in raw_candidate if c.isdigit())

            if cls.is_luhn_valid(digits):
                brand = cls.detect_brand(digits)
                matches.append({
                    "category": "PCI",
                    "detector_name": brand,
                    "confidence": "HIGH",
                    "byte_offset": match.start(),
                    "file_extension": "",
                    # Strictly no raw card numbers stored (NFR-MOD8-01)
                    "masked_preview": f"{digits[:4]}********{digits[-4:]}",
                })

        return matches

"""Unit tests for Luhn Algorithm Mod-10 Credit Card Validator (TC-MOD8-001, FR-MOD8-02)."""

import pytest
from services.mod08_dspm_classifier.internal.classifier.luhn_validator import LuhnValidator


def test_tc_mod8_001_valid_visa_vs_invalid_card_numbers():
    """TC-MOD8-001: Pass valid Visa card '4532...' and an invalid number with random digits into luhn_validator.
    
    Expected Pass Criteria:
    Valid card passes with confidence HIGH; invalid number rejected as false positive.
    """
    # Standard valid Visa test card number (passes Luhn check)
    valid_visa = "4532 0150 0000 0007"
    valid_visa_clean = "4532015000000007"

    # Random 16-digit number that fails Luhn mod-10 check
    invalid_number = "4532015000000009"

    # 1. Assert Luhn verification
    assert LuhnValidator.is_luhn_valid(valid_visa_clean) is True, "Valid Visa failed Luhn check"
    assert LuhnValidator.is_luhn_valid(invalid_number) is False, "Invalid number falsely passed Luhn check"

    # 2. Assert scanning text with both numbers
    sample_text = (
        f"Order payment details: Authorized card: {valid_visa}. "
        f"Tracking reference: {invalid_number}."
    )

    findings = LuhnValidator.scan_text(sample_text)

    # Must find exactly 1 valid card, rejecting the tracking reference as false positive
    assert len(findings) == 1, f"Expected 1 valid card finding, got {len(findings)}"
    finding = findings[0]
    assert finding["category"] == "PCI"
    assert finding["detector_name"] == "CREDIT_CARD_VISA"
    assert finding["confidence"] == "HIGH"
    assert "4532********0007" in finding["masked_preview"]
    assert valid_visa_clean not in str(finding), "Raw card number must not be present in finding object"


def test_mastercard_and_amex_detection():
    """Verifies Mastercard and Amex card validation and brand classification."""
    # Valid Mastercard test number
    valid_mastercard = "5500000000000004"
    assert LuhnValidator.is_luhn_valid(valid_mastercard) is True
    assert LuhnValidator.detect_brand(valid_mastercard) == "CREDIT_CARD_MASTERCARD"

    # Valid Amex test number
    valid_amex = "378282246310005"
    assert LuhnValidator.is_luhn_valid(valid_amex) is True
    assert LuhnValidator.detect_brand(valid_amex) == "CREDIT_CARD_AMEX"

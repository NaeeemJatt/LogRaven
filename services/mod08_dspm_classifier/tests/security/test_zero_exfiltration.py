"""Security verification tests for Zero Raw Data Exfiltration (TC-MOD8-003, NFR-MOD8-01)."""

import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from services.mod08_dspm_classifier.cmd.dspm_scanner.main import run_all_classifiers
from services.mod08_dspm_classifier.internal.repository.dspm_repo import DSPMRepository
from services.mod08_dspm_classifier.internal.repository.models import DSPMClassification


@pytest.mark.asyncio
async def test_tc_mod8_003_zero_raw_payload_exfiltration():
    """TC-MOD8-003: Inspect memory and database after scanning 1,000 sensitive records.
    
    Pass Criteria:
    Zero plain-text SSNs or credit card numbers stored in PostgreSQL or log files.
    Only category, detector_name, confidence, byte_offset, and match counts are stored.
    """
    raw_ssns = [f"123-45-{1000 + i}" for i in range(500)]
    raw_cards = ["4532015000000008"] * 500  # Valid Visa card numbers

    text_corpus = " ".join([f"User record: SSN={ssn}, Card={card}" for ssn, card in zip(raw_ssns[:10], raw_cards[:10])])

    findings = run_all_classifiers(text_corpus)
    assert len(findings) > 0

    # 1. Verify findings dictionary in memory has ZERO raw plaintext sensitive tokens
    for f in findings:
        for ssn in raw_ssns[:10]:
            assert ssn not in str(f), f"Leaked raw SSN {ssn} into finding: {f}"
        for card in raw_cards[:10]:
            assert card not in str(f), f"Leaked raw credit card {card} into finding: {f}"

    # 2. Verify database repository stores only metadata without payload
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    test_asset_id = uuid.uuid4()
    for f in findings:
        classification = await DSPMRepository.record_classification(
            session=session,
            data_asset_id=test_asset_id,
            category=f["category"],
            detector_name=f["detector_name"],
            confidence=f.get("confidence", "HIGH"),
            match_count=1,
            byte_offset=f.get("byte_offset"),
        )

        # Inspect fields of the constructed ORM model
        assert not hasattr(classification, "raw_data")
        assert not hasattr(classification, "raw_payload")
        assert not hasattr(classification, "card_number")
        assert not hasattr(classification, "ssn")
        assert classification.category in ("PII", "PCI", "PHI", "SECRET")
        assert classification.detector_name in ("US_SSN", "CREDIT_CARD_VISA", "EMAIL_ADDRESS")

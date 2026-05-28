"""Tests for SOC 2 Gemini control mapper."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.compliance.constants import SOC2_CONTROLS
from app.compliance.soc2_mapper import (
    MappingError,
    _parse_and_validate_response,
    get_overall_compliance_score,
    map_to_soc2_controls,
)


def _sample_controls_json() -> str:
    items = []
    for control in SOC2_CONTROLS:
        items.append(
            {
                "control_id": control["control_id"],
                "control_name": control["control_name"],
                "status": "PASS",
                "confidence": "HIGH",
                "evidence_references": ["MFA enforcement rate above threshold"],
                "gaps": [],
                "ai_description": f"{control['control_name']} appears satisfied based on provided evidence.",
            }
        )
    return json.dumps(items)


def test_parse_and_validate_response_all_controls():
    results = _parse_and_validate_response(_sample_controls_json())
    assert len(results) == 11
    assert {item["control_id"] for item in results} == {c["control_id"] for c in SOC2_CONTROLS}
    assert all(item["status"] == "PASS" for item in results)


def test_parse_and_validate_response_fills_missing_controls():
    partial = json.dumps(
        [
            {
                "control_id": "CC6.1",
                "control_name": SOC2_CONTROLS[0]["control_name"],
                "status": "FAIL",
                "confidence": "HIGH",
                "evidence_references": ["No MFA"],
                "gaps": ["MFA not enforced"],
                "ai_description": "Control failed.",
            }
        ]
    )
    results = _parse_and_validate_response(partial)
    assert len(results) == 11
    cc61 = next(item for item in results if item["control_id"] == "CC6.1")
    assert cc61["status"] == "FAIL"
    cc62 = next(item for item in results if item["control_id"] == "CC6.2")
    assert cc62["status"] == "PARTIAL"
    assert cc62["confidence"] == "LOW"


def test_parse_invalid_json_raises_mapping_error():
    with pytest.raises(MappingError, match="invalid JSON"):
        _parse_and_validate_response("not-json")


def test_get_overall_compliance_score():
    results = [
        {"status": "PASS"},
        {"status": "PASS"},
        {"status": "PARTIAL"},
        {"status": "FAIL"},
    ]
    score = get_overall_compliance_score(results)
    assert score["pass_count"] == 2
    assert score["fail_count"] == 1
    assert score["partial_count"] == 1
    assert score["score_percent"] == 50.0


@pytest.mark.asyncio
async def test_map_to_soc2_controls_success():
    mock_response = MagicMock()
    mock_response.text = _sample_controls_json()
    mock_response.usage_metadata = MagicMock(prompt_token_count=100, candidates_token_count=200)

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    sanitized = {
        "cloudtrail": {"total_events_reviewed": 10},
        "iam": {"total_users": 5, "mfa_enforcement_rate_percent": 80.0},
        "guardduty": {"enabled": True, "high_severity_findings": 0},
    }

    with patch("app.compliance.soc2_mapper._get_client", return_value=mock_client):
        results = await map_to_soc2_controls(sanitized)

    assert len(results) == 11
    mock_client.aio.models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_map_to_soc2_controls_retries_on_timeout():
    mock_response = MagicMock()
    mock_response.text = _sample_controls_json()
    mock_response.usage_metadata = None

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[asyncio.TimeoutError(), mock_response]
    )

    with patch("app.compliance.soc2_mapper._get_client", return_value=mock_client):
        with patch("app.compliance.soc2_mapper.asyncio.sleep", new=AsyncMock()):
            results = await map_to_soc2_controls({"cloudtrail": {}, "iam": {}, "guardduty": {}})

    assert len(results) == 11
    assert mock_client.aio.models.generate_content.await_count == 2

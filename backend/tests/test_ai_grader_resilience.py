import json
import pytest
from app.compliance import frameworks as fw
from app.compliance.ai_grader import (
    MappingError,
    _clean_json_text,
    evaluate_framework_deterministically,
    parse_and_validate,
)

def test_clean_json_text_strips_markdown():
    text = "```json\n[{\"control_id\": \"1.4\"}]\n```"
    assert _clean_json_text(text) == '[{"control_id": "1.4"}]'


def test_parse_and_validate_handles_unescaped_internal_quotes():
    # Exact scenario that broke CIS AWS scan in production:
    raw_ai_text = """[
      {
        "control_id": "1.4",
        "control_name": "Ensure no 'root' user account access key exists / root MFA enabled",
        "status": "PARTIAL",
        "confidence": "HIGH",
        "evidence_references": ["iam_root_mfa_enabled = false"],
        "gaps": ["Root account has no MFA"],
        "ai_description": "Detected policy "AdministratorAccess" assigned to users without root MFA."
      },
      {
        "control_id": "1.5",
        "control_name": "Ensure MFA is enabled for the 'root' user account",
        "status": "FAIL",
        "confidence": "HIGH",
        "evidence_references": ["iam_root_mfa_enabled = false"],
        "gaps": ["Enable hardware or virtual MFA for the root user."],
        "ai_description": "Root MFA is disabled."
      }
    ]"""

    cis = fw.get_framework("cis_aws")
    controls = [c.as_prompt_dict() for c in cis.controls]
    results = parse_and_validate(raw_ai_text, controls)

    assert len(results) == len(cis.controls)
    by_id = {r["control_id"]: r for r in results}

    assert by_id["1.4"]["status"] == "PARTIAL"
    assert by_id["1.4"]["confidence"] == "HIGH"
    assert "AdministratorAccess" in by_id["1.4"]["ai_description"]
    assert by_id["1.5"]["status"] == "FAIL"


def test_parse_and_validate_handles_trailing_commas():
    raw_ai_text = """[
      {
        "control_id": "1.4",
        "control_name": "Ensure no 'root' user account access key exists",
        "status": "PASS",
        "confidence": "HIGH",
        "evidence_references": ["iam_root_mfa_enabled = true", ],
        "gaps": [],
        "ai_description": "Root MFA is active.",
      },
    ]"""
    cis = fw.get_framework("cis_aws")
    controls = [c.as_prompt_dict() for c in cis.controls]
    results = parse_and_validate(raw_ai_text, controls)
    assert len(results) == len(cis.controls)
    by_id = {r["control_id"]: r for r in results}
    assert by_id["1.4"]["status"] == "PASS"


def test_evaluate_framework_deterministically_cis_aws():
    cis = fw.get_framework("cis_aws")
    signals = {
        "iam_root_mfa_enabled": True,
        "iam_password_policy_exists": True,
        "iam_password_min_length": 14,
        "iam_mfa_enforcement_rate": 100.0,
        "s3_default_encryption_rate": 100.0,
        "s3_public_access_blocked": True,
        "ebs_default_encryption": True,
        "rds_encryption_rate": 100.0,
        "cloudtrail_multiregion": True,
        "cloudtrail_log_validation": True,
        "cloudtrail_encrypted": True,
        "guardduty_enabled": True,
        "guardduty_high_severity_findings": 0,
        "open_security_groups": 0,
        "default_sg_restricted": True,
        "backup_configured": True,
    }

    results = evaluate_framework_deterministically(cis, signals)
    assert len(results) == len(cis.controls)

    by_id = {r["control_id"]: r for r in results}
    assert by_id["1.4"]["status"] == "PASS"
    assert by_id["1.4"]["confidence"] == "HIGH"
    assert any("iam_root_mfa_enabled = True" in ref for ref in by_id["1.4"]["evidence_references"])
    assert by_id["1.8"]["status"] == "PASS"
    assert by_id["2.1.2"]["status"] == "PASS"


def test_evaluate_framework_deterministically_soc2():
    soc2 = fw.get_framework("soc2")
    signals = {
        "iam_root_mfa_enabled": True,
        "iam_mfa_enforcement_rate": 100.0,
        "cloudtrail_multiregion": True,
        "cloudtrail_log_validation": True,
        "s3_default_encryption_rate": 100.0,
    }

    results = evaluate_framework_deterministically(soc2, signals)
    assert len(results) == len(soc2.controls)
    assert all(r["status"] in ("PASS", "FAIL", "PARTIAL") for r in results)

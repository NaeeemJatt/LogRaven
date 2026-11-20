"""
Unit tests for Module 03: Automated Qualys CSV-to-YAML Rule Compiler.
Verifies compilation logic, condition inference across 8 evaluator families, and generated YAML rule validity.
"""

from pathlib import Path
import pytest
import yaml

from app.scripts.compile_qualys_csvs import (
    compile_all,
    infer_conditions,
    assign_policies,
    parse_qualys_csv,
    CLOUDTRAIL_LOG_EVENT_MAP,
)

CATALOG_DIR = Path(__file__).resolve().parent.parent / "app" / "data" / "csv_catalog"
RULES_DIR = Path(__file__).resolve().parent.parent / "app" / "data" / "rules"


def test_compile_all_outputs_exact_counts(tmp_path):
    summary = compile_all(CATALOG_DIR, tmp_path)
    assert summary["total_rules"] == 1565
    assert summary["files_compiled"]["aws"]["count"] == 700
    assert summary["files_compiled"]["azure"]["count"] == 572
    assert summary["files_compiled"]["gcp"]["count"] == 201
    assert summary["files_compiled"]["oci"]["count"] == 92


def test_compiled_aws_rules_structure():
    aws_yaml = RULES_DIR / "cspm_aws.yaml"
    assert aws_yaml.is_file(), f"Expected compiled YAML at {aws_yaml}"

    with open(aws_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules = data.get("rules", [])
    assert len(rules) == 700

    rules_by_cid = {str(r["cid"]): r for r in rules}

    # Verify CID 18 CloudTrail Root detection
    assert "18" in rules_by_cid
    r18 = rules_by_cid["18"]
    assert r18["rule_id"] == "QUALYS-AWS-CID-18"
    assert r18["target_source"] == "aws_cloudtrail_log"
    assert r18["match_logic"] == "ALL"
    assert len(r18["conditions"]) == 2
    assert r18["conditions"][0]["field_path"] == "$.userIdentity.type"
    assert r18["conditions"][0]["operator"] == "eq"
    assert r18["conditions"][0]["value"] == "Root"

    # Verify CID 41 SSH open world detection
    assert "41" in rules_by_cid
    r41 = rules_by_cid["41"]
    assert r41["rule_id"] == "QUALYS-AWS-CID-41"
    assert r41["target_source"] == "aws_config_state"
    assert any(c["operator"] == "cidr_open_world" and c["value"] == 22 for c in r41["conditions"])

    # Verify CID 50 IAM wildcard
    assert "50" in rules_by_cid
    r50 = rules_by_cid["50"]
    assert r50["rule_id"] == "QUALYS-AWS-CID-50"
    assert any(c["operator"] == "iam_ast_wildcard" for c in r50["conditions"])

    # Verify every rule has mandates and policies
    for r in rules:
        assert len(r["mandates"]) == 38
        assert isinstance(r["policies"], list)
        assert len(r["conditions"]) >= 1


def test_infer_conditions_primitives():
    # 1. CloudTrail
    src, logic, conds = infer_conditions("18", "Root usage", "CloudTrail")
    assert src == "aws_cloudtrail_log"
    assert logic == "ALL"

    # 2. Port 22 SSH
    src, logic, conds = infer_conditions("41", "Ensure no security groups allow ingress from 0.0.0.0/0 to port 22", "VPC")
    assert src == "aws_config_state"
    assert conds[0]["operator"] == "cidr_open_world"
    assert conds[0]["value"] == 22

    # 3. Port 3389 RDP
    src, logic, conds = infer_conditions("42", "Ensure no security groups allow ingress to port 3389", "VPC")
    assert conds[0]["operator"] == "cidr_open_world"
    assert conds[0]["value"] == 3389

    # 4. IAM wildcard
    src, logic, conds = infer_conditions("50", "Ensure IAM policies that allow full *:* admin privileges are not attached", "IAM")
    assert logic == "ANY"
    assert conds[0]["operator"] == "iam_ast_wildcard"

    # 5. Customer managed key
    src, logic, conds = infer_conditions("99", "Ensure S3 buckets are encrypted with customer managed key (CMK)", "S3")
    assert conds[0]["operator"] == "kms_cmk_encrypted"

    # 6. MFA
    src, logic, conds = infer_conditions("1", "Ensure multi-factor authentication (MFA) is enabled", "IAM")
    assert conds[0]["operator"] == "eq"
    assert conds[0]["field_path"] == "$.mfa_active"

    # 7. Rotation
    src, logic, conds = infer_conditions("2", "Ensure credentials unused for 45 days are disabled", "IAM")
    assert conds[0]["operator"] == "age_days_gte"
    assert conds[0]["value"] == 45


def test_assign_policies_mapping():
    policies = parse_qualys_csv(CATALOG_DIR / "policies.csv", "POLICY TITLE")

    # AWS IAM service
    iam_policies = assign_policies("AWS", "IAM", "Run Time", policies)
    assert any("Identity" in p or "Best Practices" in p or "Foundations" in p for p in iam_policies)

    # AWS S3 service
    s3_policies = assign_policies("AWS", "S3", "Run Time", policies)
    assert any("Storage" in p or "Best Practices" in p or "Foundations" in p for p in s3_policies)

"""
Unit tests for Module 04: Unified Rule Schema & Hot-Reload Loader.
Verifies Pydantic v2 schemas, 12-operator types, RuleLoader multi-index performance, and backward compatibility.
"""

from pathlib import Path
import pytest

from app.rules.schema import (
    ConditionRule,
    DeterministicRuleSpec,
    ExecutionMode,
    OperatorType,
    RuleEvaluationResult,
    RuleDefinition,
)
from app.rules.loader import (
    RuleLoader,
    get_rules,
    load_rules,
    get_default_rule_loader,
    RULES_DIR,
)


def test_operator_type_enum_has_all_12_primitives():
    expected_operators = {
        "eq", "neq", "in", "not_in", "gte", "lte", "regex", "exists",
        "cidr_open_world", "iam_ast_wildcard", "kms_cmk_encrypted", "age_days_gte",
    }
    actual_operators = {op.value for op in OperatorType}
    assert actual_operators == expected_operators


def test_deterministic_rule_spec_pydantic_validation():
    rule = DeterministicRuleSpec(
        rule_id="QUALYS-AWS-CID-41",
        cid="41",
        title="Ensure no security groups allow ingress to port 22",
        provider="AWS",
        service="VPC",
        execution_type=ExecutionMode.RUN_TIME,
        criticality="HIGH",
        target_source="aws_config_state",
        match_logic="ALL",
        conditions=[
            ConditionRule(field_path="$.IpPermissions", operator=OperatorType.CIDR_OPEN_WORLD, value=22)
        ],
        policies=["CIS Amazon Web Services Foundations Benchmark"],
        mandates=["PCI-DSS v4.0", "SOC 2"],
    )

    assert rule.rule_id == "QUALYS-AWS-CID-41"
    assert rule.cid == "41"
    assert rule.conditions[0].operator == OperatorType.CIDR_OPEN_WORLD
    assert rule.conditions[0].value == 22


def test_rule_loader_loads_all_1565_compiled_rules():
    loader = RuleLoader(RULES_DIR)
    loaded_count = loader.load_all()

    assert loaded_count >= 1565, f"Expected at least 1565 rules, loaded {loaded_count}"
    assert len(loader.rules_by_cid) >= 1565

    # Check rule by CID
    r18 = loader.get_rule_by_cid("18")
    assert r18 is not None
    assert r18.rule_id == "QUALYS-AWS-CID-18"
    assert r18.target_source == "aws_cloudtrail_log"

    r41 = loader.get_rule_by_cid("41")
    assert r41 is not None
    assert r41.service == "VPC"

    r50 = loader.get_rule_by_cid("50")
    assert r50 is not None
    assert r50.service == "IAM"


def test_rule_loader_indexed_lookups():
    loader = RuleLoader(RULES_DIR)
    loader.load_all()

    # Test get_rules_for_service
    iam_rules = loader.get_rules_for_service("AWS", "IAM", "aws_config_state")
    assert len(iam_rules) > 0
    assert all(r.service.upper() == "IAM" for r in iam_rules)

    # Test get_log_rules
    log_rules = loader.get_log_rules("AWS")
    assert len(log_rules) >= 15  # CID 18, 27-40
    log_cids = {r.cid for r in log_rules}
    assert "18" in log_cids
    assert "27" in log_cids
    assert "28" in log_cids
    assert "30" in log_cids


def test_detection_rules_backward_compatibility():
    # Verify existing detection rule schema and match types still work without errors
    rule_dict = {
        "id": "DET-001",
        "title": "Suspicious Process Spawn",
        "severity": "high",
        "match": {
            "type": "simple",
            "conditions": [{"field": "event_type", "op": "eq", "value": "process_create"}],
        },
    }
    r_def = RuleDefinition(**rule_dict)
    assert r_def.id == "DET-001"
    assert r_def.match.type == "simple"
    assert r_def.match.conditions[0].op == "eq"

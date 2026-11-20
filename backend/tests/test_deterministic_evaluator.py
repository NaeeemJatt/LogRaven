"""
Unit tests for Module 05: 12-Operator Pure-Python Deterministic Evaluator.
Verifies all 12 comparison operators, path extraction, IAM AST wildcard analysis, CIDR open world checks,
and rule match logic (ALL, ANY, NONE).
"""

from datetime import datetime, timedelta, timezone
import json
import pytest
from urllib.parse import quote

from app.rules.schema import (
    ConditionRule,
    DeterministicRuleSpec,
    ExecutionMode,
    OperatorType,
)
from app.rules.evaluator import (
    extract_path,
    check_iam_ast_wildcard,
    check_cidr_open_world,
    evaluate_condition,
    evaluate_rule,
)


def test_extract_path_nested_and_wildcards():
    data = {
        "userIdentity": {
            "type": "Root",
            "arn": "arn:aws:iam::123456789012:root",
        },
        "PolicyDocuments": [
            {"Statement": [{"Action": "s3:*", "Effect": "Allow"}]},
            {"Statement": [{"Action": "ec2:*", "Effect": "Allow"}]},
        ],
        "tags": {"Environment": "Production", "Owner": "SecOps"},
    }

    assert extract_path(data, "$") == data
    assert extract_path(data, "$.userIdentity.type") == "Root"
    assert extract_path(data, "$.userIdentity.arn") == "arn:aws:iam::123456789012:root"
    assert extract_path(data, "$.non.existent.path") is None

    # Array wildcard
    docs = extract_path(data, "$.PolicyDocuments.*")
    assert isinstance(docs, list)
    assert len(docs) == 2


def test_check_iam_ast_wildcard():
    # 1. Full admin: Action * and Resource *
    full_admin_doc = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
    }
    assert check_iam_ast_wildcard(full_admin_doc, "full_admin") is True
    assert check_iam_ast_wildcard(full_admin_doc, "service_or_full_wildcard") is True

    # 2. Service wildcard: Action s3:* and Resource *
    service_wildcard_doc = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}],
    }
    assert check_iam_ast_wildcard(service_wildcard_doc, "full_admin") is False
    assert check_iam_ast_wildcard(service_wildcard_doc, "service_or_full_wildcard") is True

    # 3. Deny effect should not trigger violation
    deny_doc = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
    }
    assert check_iam_ast_wildcard(deny_doc) is False

    # 4. URL-encoded string support
    url_encoded = quote(json.dumps(service_wildcard_doc))
    assert check_iam_ast_wildcard(url_encoded, "service_or_full_wildcard") is True


def test_check_cidr_open_world():
    # Security group with Port 22 open to 0.0.0.0/0
    open_ssh = [
        {
            "FromPort": 22,
            "ToPort": 22,
            "IpProtocol": "tcp",
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
        }
    ]
    assert check_cidr_open_world(open_ssh, 22) is True
    assert check_cidr_open_world(open_ssh, 443) is False
    assert check_cidr_open_world(open_ssh, None) is True

    # All traffic (-1) open to IPv6 ::/0
    open_ipv6_all = [
        {
            "IpProtocol": "-1",
            "Ipv6Ranges": [{"CidrIpv6": "::/0"}],
        }
    ]
    assert check_cidr_open_world(open_ipv6_all, 22) is True
    assert check_cidr_open_world(open_ipv6_all, 80) is True

    # Restricted internal CIDR
    locked_sg = [
        {
            "FromPort": 22,
            "ToPort": 22,
            "IpProtocol": "tcp",
            "IpRanges": [{"CidrIp": "10.0.0.0/8"}, {"CidrIp": "172.16.0.0/12"}],
        }
    ]
    assert check_cidr_open_world(locked_sg, 22) is False


def test_evaluate_condition_all_operators():
    payload = {
        "status": "active",
        "count": 42,
        "name": "prod-database-primary",
        "role": "admin",
        "roles": ["dev", "admin", "audit"],
        "encrypted_aws": {
            "StorageEncrypted": True,
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:alias/aws/rds",
        },
        "encrypted_cmk": {
            "StorageEncrypted": True,
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        },
        "old_key_date": (datetime.now(timezone.utc) - timedelta(days=120)).isoformat(),
        "new_key_date": (datetime.now(timezone.utc) - timedelta(days=15)).isoformat(),
    }

    # 1. exists
    assert evaluate_condition(payload, ConditionRule(field_path="$.status", operator=OperatorType.EXISTS, value=True)) is True
    assert evaluate_condition(payload, ConditionRule(field_path="$.missing", operator=OperatorType.EXISTS, value=False)) is True

    # 2. eq / neq
    assert evaluate_condition(payload, ConditionRule(field_path="$.status", operator=OperatorType.EQ, value="active")) is True
    assert evaluate_condition(payload, ConditionRule(field_path="$.status", operator=OperatorType.NEQ, value="inactive")) is True

    # 3. in / not_in
    assert evaluate_condition(payload, ConditionRule(field_path="$.role", operator=OperatorType.IN, value=["admin", "secops"])) is True
    assert evaluate_condition(payload, ConditionRule(field_path="$.roles", operator=OperatorType.IN, value=["audit"])) is True
    assert evaluate_condition(payload, ConditionRule(field_path="$.role", operator=OperatorType.NOT_IN, value=["guest"])) is True

    # 4. gte / lte
    assert evaluate_condition(payload, ConditionRule(field_path="$.count", operator=OperatorType.GTE, value=40)) is True
    assert evaluate_condition(payload, ConditionRule(field_path="$.count", operator=OperatorType.LTE, value=50)) is True

    # 5. regex
    assert evaluate_condition(payload, ConditionRule(field_path="$.name", operator=OperatorType.REGEX, value=r"^prod-.*-primary$")) is True

    # 6. kms_cmk_encrypted
    assert evaluate_condition(payload, ConditionRule(field_path="$.encrypted_aws", operator=OperatorType.KMS_CMK_ENCRYPTED, value=True)) is False
    assert evaluate_condition(payload, ConditionRule(field_path="$.encrypted_cmk", operator=OperatorType.KMS_CMK_ENCRYPTED, value=True)) is True

    # 7. age_days_gte
    assert evaluate_condition(payload, ConditionRule(field_path="$.old_key_date", operator=OperatorType.AGE_DAYS_GTE, value=90)) is True
    assert evaluate_condition(payload, ConditionRule(field_path="$.new_key_date", operator=OperatorType.AGE_DAYS_GTE, value=90)) is False


def test_evaluate_rule_all_any_none_logic():
    rule_all = DeterministicRuleSpec(
        rule_id="R-ALL",
        title="Test ALL logic",
        service="EC2",
        match_logic="ALL",
        conditions=[
            ConditionRule(field_path="$.env", operator=OperatorType.EQ, value="prod"),
            ConditionRule(field_path="$.exposed", operator=OperatorType.EQ, value=True),
        ],
    )
    assert evaluate_rule({"env": "prod", "exposed": True}, rule_all) is True
    assert evaluate_rule({"env": "prod", "exposed": False}, rule_all) is False

    rule_any = DeterministicRuleSpec(
        rule_id="R-ANY",
        title="Test ANY logic",
        service="EC2",
        match_logic="ANY",
        conditions=[
            ConditionRule(field_path="$.port", operator=OperatorType.EQ, value=22),
            ConditionRule(field_path="$.port", operator=OperatorType.EQ, value=3389),
        ],
    )
    assert evaluate_rule({"port": 22}, rule_any) is True
    assert evaluate_rule({"port": 3389}, rule_any) is True
    assert evaluate_rule({"port": 443}, rule_any) is False

    rule_none = DeterministicRuleSpec(
        rule_id="R-NONE",
        title="Test NONE logic",
        service="EC2",
        match_logic="NONE",
        conditions=[
            ConditionRule(field_path="$.firewall", operator=OperatorType.EQ, value="disabled"),
        ],
    )
    assert evaluate_rule({"firewall": "active"}, rule_none) is True
    assert evaluate_rule({"firewall": "disabled"}, rule_none) is False

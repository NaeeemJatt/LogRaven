"""Unit tests for Visual-to-Rego Studio Compiler (TC-MOD12-001).

Compiles visual condition trees into valid Open Policy Agent (OPA) Rego strings.
"""

import pytest

from services.mod12_policy_vault.internal.rego_studio.rego_compiler import RegoCompiler


def test_tc_mod12_001_compile_s3_versioning_rule():
    """TC-MOD12-001: Visual rule: S3 bucket where versioning.status != 'Enabled'.

    Expected: Compiler outputs valid Rego string:
      package lograven.rules.custom ... deny[msg] { input.versioning.status != "Enabled" }
    """
    rule_id = "CUSTOM-S3-VERSIONING"
    resource_type = "aws_s3_bucket"
    conditions = [
        {"field": "versioning.status", "operator": "!=", "value": "Enabled"}
    ]
    message = "S3 bucket versioning is not enabled"

    rego_output = RegoCompiler.compile_rule(
        rule_id=rule_id,
        resource_type=resource_type,
        conditions=conditions,
        message=message,
    )

    # 1. Package header and default allow
    assert "package lograven.rules.custom" in rego_output
    assert "default allow = true" in rego_output

    # 2. Deny rule block
    assert "deny[msg] {" in rego_output
    assert 'input.resource_type == "aws_s3_bucket"' in rego_output
    assert 'input.versioning.status != "Enabled"' in rego_output
    assert 'msg := "S3 bucket versioning is not enabled"' in rego_output


def test_compile_multiple_conditions():
    """Verifies compiling multiple boolean, numeric, and string conditions."""
    rego = RegoCompiler.compile_rule(
        rule_id="CUSTOM-EC2-CHECK",
        resource_type="aws_instance",
        conditions=[
            {"field": "instance_type", "operator": "==", "value": "t2.micro"},
            {"field": "ebs_optimized", "operator": "==", "value": False},
            {"field": "volume_size", "operator": ">=", "value": 100},
        ],
    )
    assert 'input.instance_type == "t2.micro"' in rego
    assert "input.ebs_optimized == false" in rego
    assert "input.volume_size >= 100" in rego


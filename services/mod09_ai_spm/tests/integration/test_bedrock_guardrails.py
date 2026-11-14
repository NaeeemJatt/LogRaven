"""Integration tests for AI Guardrails and Logging Posture (TC-MOD9-003).

Audits AWS Bedrock endpoints for prompt injection guardrail associations and CloudWatch invocation logging.
"""

import pytest

from services.mod09_ai_spm.internal.ai_inventory.bedrock_enumerator import BedrockEnumerator


def test_tc_mod9_003_bedrock_missing_guardrail_and_logging():
    """TC-MOD9-003: AWS Bedrock endpoint deployed without Guardrail association and CloudWatch logging disabled.

    Expected: Evaluator generates two Medium IOM findings: AI_MISSING_GUARDRAIL and AI_LOGGING_DISABLED.
    """
    endpoint_urn = "arn:aws:bedrock:us-east-1:112233445566:custom-model/customer-support-llm-v1"
    model_name = "customer-support-llm-v1"

    # Evaluated without guardrail and with logging disabled
    eval_result = BedrockEnumerator.evaluate_model_posture(
        endpoint_urn=endpoint_urn,
        model_name=model_name,
        guardrail_identifier=None,
        logging_config={"cloudwatch_logging_enabled": False},
    )

    assert eval_result["guardrails_enabled"] is False
    assert eval_result["prompt_logging_enabled"] is False
    assert eval_result["is_compliant"] is False

    findings = eval_result["findings"]
    assert len(findings) == 2

    finding_map = {f["finding_code"]: f for f in findings}
    assert "AI_MISSING_GUARDRAIL" in finding_map
    assert "AI_LOGGING_DISABLED" in finding_map

    # Both findings must be Medium severity IOMs
    assert finding_map["AI_MISSING_GUARDRAIL"]["severity"] == "MEDIUM"
    assert finding_map["AI_MISSING_GUARDRAIL"]["category"] == "IOM"
    assert finding_map["AI_LOGGING_DISABLED"]["severity"] == "MEDIUM"
    assert finding_map["AI_LOGGING_DISABLED"]["category"] == "IOM"


def test_bedrock_compliant_endpoint():
    """Verifies that an AWS Bedrock endpoint with guardrails and logging enabled passes posture audit."""
    endpoint_urn = "arn:aws:bedrock:us-east-1:112233445566:custom-model/secure-banking-assistant"
    model_name = "secure-banking-assistant"

    eval_result = BedrockEnumerator.evaluate_model_posture(
        endpoint_urn=endpoint_urn,
        model_name=model_name,
        guardrail_identifier="gr-7a8b9c0d1e2f",
        logging_config={
            "cloudWatchConfig": {
                "logGroupName": "/aws/bedrock/model-invocations",
                "roleArn": "arn:aws:iam::112233445566:role/BedrockCWLoggingRole",
            }
        },
    )

    assert eval_result["guardrails_enabled"] is True
    assert eval_result["prompt_logging_enabled"] is True
    assert eval_result["is_compliant"] is True
    assert len(eval_result["findings"]) == 0

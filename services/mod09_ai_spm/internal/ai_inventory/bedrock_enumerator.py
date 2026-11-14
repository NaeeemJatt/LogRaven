"""AWS Bedrock Model & Guardrail Enumerator (PRD-MOD-09 / TC-MOD9-003).

Discovers Bedrock foundation models, custom models, guardrails, and model invocation logging.
"""

from typing import Any, Dict, List, Optional


class BedrockEnumerator:
    """Audits AWS Bedrock endpoints for guardrail protection and invocation logging."""

    @classmethod
    def evaluate_model_posture(
        cls,
        endpoint_urn: str,
        model_name: str,
        guardrail_identifier: Optional[str] = None,
        logging_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Audits an AWS Bedrock endpoint/model deployment."""
        findings: List[Dict[str, Any]] = []

        # 1. Guardrail association check
        guardrails_enabled = bool(guardrail_identifier and guardrail_identifier.strip())
        if not guardrails_enabled:
            findings.append({
                "finding_code": "AI_MISSING_GUARDRAIL",
                "severity": "MEDIUM",
                "category": "IOM",
                "resource_urn": endpoint_urn,
                "description": f"AWS Bedrock endpoint '{model_name}' has no Guardrail associated to filter prompt injections or sensitive data leakage.",
            })

        # 2. Invocation logging check
        cloudwatch_enabled = False
        if logging_config:
            cloudwatch_enabled = bool(
                logging_config.get("cloudWatchConfig", {}).get("logGroupName") or
                logging_config.get("cloudwatch_logging_enabled") or
                logging_config.get("logging_enabled")
            )

        if not cloudwatch_enabled:
            findings.append({
                "finding_code": "AI_LOGGING_DISABLED",
                "severity": "MEDIUM",
                "category": "IOM",
                "resource_urn": endpoint_urn,
                "description": f"AWS Bedrock endpoint '{model_name}' has invocation audit logging disabled.",
            })

        return {
            "endpoint_urn": endpoint_urn,
            "provider": "aws_bedrock",
            "model_name": model_name,
            "guardrails_enabled": guardrails_enabled,
            "prompt_logging_enabled": cloudwatch_enabled,
            "findings": findings,
            "is_compliant": len(findings) == 0,
        }

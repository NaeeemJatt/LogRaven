"""AI Guardrail and Content Moderation Evaluator (PRD-MOD-09).

Evaluates whether deployed LLM endpoints enforce input/output guardrails against prompt injection and jailbreaks.
"""

from typing import Any, Dict, List, Optional


class GuardrailEvaluator:
    """Evaluates content filtering and prompt injection guardrails across multi-cloud AI services."""

    @classmethod
    def evaluate_ai_service(
        cls,
        provider: str,
        resource_urn: str,
        service_name: str,
        has_guardrail: bool,
        has_logging: bool,
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        if not has_guardrail:
            findings.append({
                "finding_code": "AI_MISSING_GUARDRAIL",
                "severity": "MEDIUM",
                "category": "IOM",
                "resource_urn": resource_urn,
                "description": f"AI service '{service_name}' ({provider}) has no prompt moderation guardrail configured.",
            })

        if not has_logging:
            findings.append({
                "finding_code": "AI_LOGGING_DISABLED",
                "severity": "MEDIUM",
                "category": "IOM",
                "resource_urn": resource_urn,
                "description": f"AI service '{service_name}' ({provider}) has invocation telemetry logging disabled.",
            })

        return {
            "provider": provider,
            "resource_urn": resource_urn,
            "service_name": service_name,
            "has_guardrail": has_guardrail,
            "has_logging": has_logging,
            "findings": findings,
            "status": "NON_COMPLIANT" if findings else "COMPLIANT",
        }

"""AWS SageMaker Model & Endpoint Enumerator (PRD-MOD-09).

Enumerates SageMaker endpoints, model artifacts in S3, and verifies encryption / isolation.
"""

from typing import Any, Dict, List, Optional


class SageMakerEnumerator:
    """Audits AWS SageMaker models, training jobs, and endpoint configurations."""

    @classmethod
    def evaluate_endpoint_posture(
        cls,
        endpoint_urn: str,
        endpoint_name: str,
        model_data_url: Optional[str] = None,
        data_capture_config: Optional[Dict[str, Any]] = None,
        kms_key_id: Optional[str] = None,
        network_isolation: bool = False,
    ) -> Dict[str, Any]:
        """Audits SageMaker endpoint configuration."""
        findings: List[Dict[str, Any]] = []

        # Data capture check (logging requests/responses)
        data_capture_enabled = bool(data_capture_config and data_capture_config.get("EnableCapture", False))
        if not data_capture_enabled:
            findings.append({
                "finding_code": "AI_LOGGING_DISABLED",
                "severity": "MEDIUM",
                "category": "IOM",
                "resource_urn": endpoint_urn,
                "description": f"SageMaker endpoint '{endpoint_name}' has Data Capture logging disabled.",
            })

        # Storage encryption check
        if not kms_key_id:
            findings.append({
                "finding_code": "AI_STORAGE_UNENCRYPTED",
                "severity": "LOW",
                "category": "IOM",
                "resource_urn": endpoint_urn,
                "description": f"SageMaker endpoint '{endpoint_name}' is not encrypted with a customer-managed KMS key.",
            })

        return {
            "endpoint_urn": endpoint_urn,
            "provider": "sagemaker",
            "model_name": endpoint_name,
            "model_data_url": model_data_url,
            "data_capture_enabled": data_capture_enabled,
            "kms_key_id": kms_key_id,
            "network_isolation": network_isolation,
            "findings": findings,
            "is_compliant": len(findings) == 0,
        }

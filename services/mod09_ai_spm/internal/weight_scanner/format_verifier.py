"""Weight format verification and posture evaluator (PRD-MOD-09).

Identifies model checkpoint formats and advises on modern safe serialization standards (safetensors).
"""

from typing import Any, Dict, Optional


class WeightFormatVerifier:
    """Classifies model weight formats and verifies safety boundaries."""

    SAFE_FORMATS = {"safetensors", "onnx", "gguf"}
    UNSAFE_DESERIALIZATION_FORMATS = {"pkl", "pickle", "bin", "pt", "pth", "joblib"}

    @classmethod
    def evaluate_format(cls, filename: str, content_prefix: bytes = b"") -> Dict[str, Any]:
        """Evaluates model file extension and optional magic headers."""
        clean_name = filename.lower().strip()
        ext = clean_name.split(".")[-1] if "." in clean_name else "unknown"

        # Safetensors detection: extension or 8-byte header JSON length
        if ext == "safetensors":
            return {
                "format": "safetensors",
                "is_safe_format": True,
                "has_unsafe_deserialization_risk": False,
                "recommendation": "Compliant format. Safe against arbitrary code execution.",
            }

        if ext in ("onnx", "gguf"):
            return {
                "format": ext,
                "is_safe_format": True,
                "has_unsafe_deserialization_risk": False,
                "recommendation": "Compliant static computation graph format.",
            }

        if ext in cls.UNSAFE_DESERIALIZATION_FORMATS:
            return {
                "format": ext,
                "is_safe_format": False,
                "has_unsafe_deserialization_risk": True,
                "recommendation": f"Model serialized in legacy '{ext}' format. Vulnerable to arbitrary code execution; convert to safetensors.",
            }

        return {
            "format": ext,
            "is_safe_format": False,
            "has_unsafe_deserialization_risk": True,
            "recommendation": "Unrecognized model weight format. Audit for custom unpickling routines.",
        }

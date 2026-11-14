"""Integration tests for Statistically Bounded Reservoir Sampling (TC-MOD8-002, FR-MOD8-01)."""

import time
import pytest

from services.mod08_dspm_classifier.cmd.dspm_scanner.main import run_all_classifiers
from services.mod08_dspm_classifier.internal.sampler.reservoir import ReservoirSampler


def test_tc_mod8_002_reservoir_sampling_10k_files():
    """TC-MOD8-002: Seed mock S3 bucket with 10,000 files including 1 file with unencrypted API keys.
    
    Pass Criteria:
    1. Sampler processes exactly k = 200 files.
    2. Scans in < 15 seconds.
    3. Creates classification record without storing raw text.
    """
    total_files = 10000
    mock_files = {f"logs/2026/object_{i}.log": f"Standard cloud log record {i}" for i in range(total_files)}

    # Inject 1 sensitive file containing plaintext AWS access key
    secret_key = "logs/2026/object_42.log"
    plaintext_key = "AKIAIOSFODNN7EXAMPLE"
    mock_files[secret_key] = f"AWS_ACCESS_KEY_ID={plaintext_key}\nEnvironment=Production"

    start_time = time.perf_counter()

    # 1. Apply Reservoir Sampler (Algorithm R, k=200)
    # Using seed to ensure deterministic inclusion of target or testing random sampling
    sampler = ReservoirSampler(k=200, seed=42)
    sampled_keys = sampler.sample(list(mock_files.keys()))

    # Always ensure the sample size is bounded to exactly k = 200
    assert len(sampled_keys) == 200, f"Expected exactly 200 sampled keys, got {len(sampled_keys)}"

    # 2. Process all sampled files in memory
    total_findings = []
    for key in sampled_keys:
        content = mock_files[key]
        findings = run_all_classifiers(content)
        total_findings.extend(findings)

    elapsed_time = time.perf_counter() - start_time

    # Performance criteria: < 15 seconds (usually < 0.1s in memory)
    assert elapsed_time < 15.0, f"Scan took {elapsed_time:.3f}s, target was < 15.0s"

    # Also directly scan the secret file to verify classification record formatting
    secret_findings = run_all_classifiers(mock_files[secret_key])
    assert len(secret_findings) == 1
    finding = secret_findings[0]
    assert finding["category"] == "SECRET"
    assert finding["detector_name"] == "AWS_ACCESS_KEY_ID"
    assert finding["confidence"] == "HIGH"
    # Zero raw text storage verification
    assert plaintext_key not in str(finding), "Plaintext API key leaked into classification finding!"

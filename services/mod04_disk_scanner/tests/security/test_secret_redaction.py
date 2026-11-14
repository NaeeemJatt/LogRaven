"""Security tests for Secret Detection and Plaintext Masking (TC-MOD4-003)."""

from services.mod04_disk_scanner.internal.secret_scanner.pattern_matcher import SecretScanner, mask_secret


def test_tc_mod4_003_plaintext_aws_key_redaction_and_masking():
    """TC-MOD4-003: Place plaintext AWS access key in /home/ubuntu/.aws/credentials on disk image.
    
    Pass Criteria: Secret scanner flags finding SECRET_AWS_KEY, stores masked value
    AKIA************1234, and never logs/stores secret in plaintext.
    """
    raw_plaintext_key = "AKIAIOSFODNN7EXA1234"
    credentials_file_content = (
        "[default]\n"
        f"aws_access_key_id = {raw_plaintext_key}\n"
        "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"
        "region = us-east-1\n"
    )

    findings = SecretScanner.scan_content(
        file_path="/home/ubuntu/.aws/credentials",
        content=credentials_file_content,
    )

    assert len(findings) >= 1

    # Verify AWS key finding
    aws_findings = [f for f in findings if f["rule_id"] == "SECRET_AWS_KEY"]
    assert len(aws_findings) == 1
    hit = aws_findings[0]

    assert hit["file_path"] == "/home/ubuntu/.aws/credentials"
    assert hit["severity"] == "CRITICAL"

    # Redaction checks:
    # 1. Plaintext must NOT appear in masked_value
    assert raw_plaintext_key not in hit["masked_value"]
    # 2. Masked format preserves prefix AKIA and last 4 characters 1234
    assert hit["masked_value"].startswith("AKIA")
    assert hit["masked_value"].endswith("1234")
    assert hit["masked_value"] == "AKIA************1234"
    # 3. Cryptographic SHA-256 fingerprint generated
    assert len(hit["fingerprint"]) == 16


def test_private_key_detection_and_masking():
    """Verifies unencrypted PEM private keys are detected and redacted."""
    rsa_private_key = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y3w6B1W2...MOCK_PRIVATE_KEY_DATA...XYZ789\n"
        "-----END RSA PRIVATE KEY-----"
    )

    findings = SecretScanner.scan_content(
        file_path="/root/.ssh/id_rsa",
        content=rsa_private_key,
    )

    priv_hits = [f for f in findings if f["rule_id"] == "SECRET_PRIVATE_KEY"]
    assert len(priv_hits) == 1
    assert priv_hits[0]["file_path"] == "/root/.ssh/id_rsa"
    assert priv_hits[0]["severity"] == "CRITICAL"
    assert "MOCK_PRIVATE_KEY_DATA" not in priv_hits[0]["masked_value"]


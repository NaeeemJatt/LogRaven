"""Security tests for Cryptographic Evidence Vault Tamper Detection (TC-MOD12-004).

Verifies that modifying a single byte inside evidence.json causes SHA-256 and Merkle root verification failure.
"""

import io
import zipfile
import pytest

from services.mod12_policy_vault.internal.audit_vault.manifest_signer import ManifestSigner


def test_tc_mod12_004_single_byte_tampering_detected():
    """TC-MOD12-004: Generate Evidence Vault ZIP; alter a single byte in evidence.json inside archive.

    Expected: Vault verifier detects checksum mismatch; rejects package as corrupted/tampered.
    """
    # 1. Generate clean Evidence Vault ZIP
    original_files = {
        "evidence.json": b'{"compliance_score": 98.5, "tamper_resistant": true}',
        "soc2_report.pdf": b"%PDF-1.4 simulated report binary stream",
    }
    sealed_zip = ManifestSigner.create_vault_package(
        files=original_files,
        package_name="soc2_q4_audit_vault",
    )

    # Verify original clean package passes
    clean_check = ManifestSigner.verify_package_integrity(sealed_zip)
    assert clean_check["is_valid"] is True
    assert clean_check["status"] == "VERIFIED"
    assert clean_check["verified_files_count"] == 2

    # 2. Tamper: alter a single byte inside evidence.json
    in_buf = io.BytesIO(sealed_zip)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(in_buf, "r") as zin, zipfile.ZipFile(out_buf, "w") as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "evidence.json":
                # Flip 98.5 -> 99.5 (tampering!)
                tampered_content = content.replace(b"98.5", b"99.5")
                zout.writestr(item, tampered_content)
            else:
                zout.writestr(item, content)

    tampered_zip = out_buf.getvalue()

    # 3. Verify tampered package is rejected
    tamper_check = ManifestSigner.verify_package_integrity(tampered_zip)

    assert tamper_check["is_valid"] is False
    assert tamper_check["status"] == "TAMPERED_OR_CORRUPT"
    assert len(tamper_check["errors"]) > 0
    assert any("Checksum mismatch for 'evidence.json'" in err for err in tamper_check["errors"])


"""Cryptographic Manifest Signer & Merkle Tree Vault Verifier (PRD-MOD-12 / TC-MOD12-004).

Packages compliance evidence into ZIP archives with SHA-256 file digests and Merkle root hashes,
and detects any single-byte tampering in audit packages.
"""

from datetime import datetime, timezone
import hashlib
import io
import json
from typing import Any, Dict, List, Optional, Tuple
import zipfile


class ManifestSigner:
    """Computes Merkle trees and verifies cryptographic tamper-resistance of evidence vaults."""

    @classmethod
    def compute_merkle_root(cls, hashes: List[str]) -> str:
        """Computes a deterministic SHA-256 Merkle root from a list of hex digests."""
        if not hashes:
            return hashlib.sha256(b"").hexdigest()

        current_level = sorted(hashes)

        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    combined = (current_level[i] + current_level[i + 1]).encode("utf-8")
                else:
                    # Odd number of leaves: hash with itself
                    combined = (current_level[i] + current_level[i]).encode("utf-8")
                next_level.append(hashlib.sha256(combined).hexdigest())
            current_level = next_level

        return current_level[0]

    @classmethod
    def create_vault_package(
        cls,
        files: Dict[str, bytes],
        package_name: str = "evidence_vault",
    ) -> bytes:
        """Assembles files into a cryptographically sealed ZIP archive with manifest.json."""
        file_hashes: Dict[str, str] = {}
        for fname, content in files.items():
            digest = hashlib.sha256(content).hexdigest()
            file_hashes[fname] = digest

        merkle_root = cls.compute_merkle_root(list(file_hashes.values()))

        manifest_data = {
            "package_name": package_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_hashes": file_hashes,
            "merkle_root": merkle_root,
        }
        manifest_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")

        # Create ZIP in memory
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fname, content in files.items():
                zf.writestr(fname, content)
            zf.writestr("manifest.json", manifest_bytes)

        return zip_buf.getvalue()

    @classmethod
    def verify_package_integrity(cls, zip_bytes: bytes) -> Dict[str, Any]:
        """Validates that all files in archive match manifest SHA-256 and Merkle root."""
        errors: List[str] = []

        try:
            zip_buf = io.BytesIO(zip_bytes)
            with zipfile.ZipFile(zip_buf, mode="r") as zf:
                file_names = zf.namelist()

                if "manifest.json" not in file_names:
                    return {
                        "is_valid": False,
                        "status": "TAMPERED_OR_CORRUPT",
                        "errors": ["manifest.json is missing from evidence package."],
                    }

                manifest_raw = zf.read("manifest.json")
                manifest = json.loads(manifest_raw.decode("utf-8"))

                expected_hashes: Dict[str, str] = manifest.get("file_hashes", {})
                expected_merkle = manifest.get("merkle_root", "")

                actual_hashes: Dict[str, str] = {}
                for fname in expected_hashes.keys():
                    if fname not in file_names:
                        errors.append(f"Manifest file '{fname}' is missing from ZIP archive.")
                        continue

                    actual_content = zf.read(fname)
                    actual_digest = hashlib.sha256(actual_content).hexdigest()
                    actual_hashes[fname] = actual_digest

                    if actual_digest != expected_hashes[fname]:
                        errors.append(
                            f"Checksum mismatch for '{fname}': expected {expected_hashes[fname]}, got {actual_digest}"
                        )

                # Verify Merkle Root
                computed_merkle = cls.compute_merkle_root(list(actual_hashes.values()))
                if computed_merkle != expected_merkle:
                    errors.append(
                        f"Merkle root mismatch: expected {expected_merkle}, computed {computed_merkle}"
                    )

                if errors:
                    return {
                        "is_valid": False,
                        "status": "TAMPERED_OR_CORRUPT",
                        "errors": errors,
                        "manifest": manifest,
                    }

                return {
                    "is_valid": True,
                    "status": "VERIFIED",
                    "merkle_root": computed_merkle,
                    "verified_files_count": len(actual_hashes),
                    "manifest": manifest,
                }

        except Exception as err:
            return {
                "is_valid": False,
                "status": "TAMPERED_OR_CORRUPT",
                "errors": [f"Failed to inspect zip package: {str(err)}"],
            }


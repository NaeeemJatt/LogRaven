"""Unit tests for Terraform HCL AST Patcher (TC-MOD11-001).

Verifies surgical attribute flipping while preserving comments, indentation, and formatting.
"""

import pytest

from services.mod11_iac_gitops.internal.pr_generator.ast_patcher import ASTPatcher


def test_tc_mod11_001_s3_block_public_acls_patch():
    """TC-MOD11-001: Pass Terraform HCL defining S3 bucket with block_public_acls = false into ast_patcher.

    Expected: Patcher returns clean diff flipping attribute to true while preserving surrounding comments and indentation.
    """
    initial_hcl = (
        '# Production Customer Data Lake Bucket\n'
        'resource "aws_s3_bucket_public_access_block" "customer_data" {\n'
        '  bucket = aws_s3_bucket.customer_data.id\n'
        '\n'
        '  # Critical Security Setting: Block public ACLs\n'
        '  block_public_acls       = false\n'
        '  block_public_policy     = true\n'
        '  ignore_public_acls      = true\n'
        '  restrict_public_buckets = true\n'
        '}\n'
    )

    # Patch block_public_acls to true
    result = ASTPatcher.patch_attribute(
        hcl_content=initial_hcl,
        attribute="block_public_acls",
        new_value=True,
    )

    assert result["modified"] is True
    patched = result["patched_content"]

    # 1. Attribute flipped to true with identical indentation
    assert "  block_public_acls       = true\n" in patched

    # 2. Surrounding comments strictly preserved
    assert "# Production Customer Data Lake Bucket" in patched
    assert "# Critical Security Setting: Block public ACLs" in patched

    # 3. Other attributes untouched
    assert "block_public_policy     = true" in patched
    assert "restrict_public_buckets = true" in patched

    # 4. Clean diff generated
    diff = result["diff"]
    assert "-  block_public_acls       = false" in diff
    assert "+  block_public_acls       = true" in diff


def test_patch_key_rotation():
    """Verifies flipping enable_key_rotation on aws_kms_key block."""
    initial_hcl = (
        'resource "aws_kms_key" "primary" {\n'
        '  description             = "KMS Key 1"\n'
        '  enable_key_rotation     = false\n'
        '}\n'
    )
    result = ASTPatcher.patch_attribute(
        hcl_content=initial_hcl,
        attribute="enable_key_rotation",
        new_value=True,
    )
    assert result["modified"] is True
    assert "  enable_key_rotation     = true\n" in result["patched_content"]

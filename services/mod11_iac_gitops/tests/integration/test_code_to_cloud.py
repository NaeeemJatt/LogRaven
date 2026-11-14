"""Integration tests for Code-to-Cloud Lineage Correlation (TC-MOD11-002).

Correlates cloud asset tags (git_repo, git_file) to Git repository and identifies line number in source files.
"""

import pytest

from services.mod11_iac_gitops.internal.lineage_tracker.fuzzy_ast_matcher import FuzzyASTMatcher
from services.mod11_iac_gitops.internal.lineage_tracker.tag_correlator import TagCorrelator


def test_tc_mod11_002_code_to_cloud_lineage_correlation():
    """TC-MOD11-002: Asset has tag git_repo=acme/infra and git_file=main.tf.

    Expected: Lineage tracker correlates to git_repositories entry and identifies line 42 in main.tf.
    """
    asset_tags = {
        "git_repo": "acme/infra",
        "git_file": "main.tf",
        "git_commit": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4",
        "git_line": "42",
        "Environment": "Production",
    }

    # 1. Extract GitOps metadata from tags
    meta = TagCorrelator.extract_git_metadata(asset_tags)

    assert meta["has_lineage"] is True
    assert meta["repo_full_name"] == "acme/infra"
    assert meta["file_path"] == "main.tf"
    assert meta["line_number"] == 42
    assert meta["commit_sha"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4"


def test_fuzzy_ast_matcher_locates_exact_lines():
    """Verifies FuzzyASTMatcher locates resource block when tag lacks explicit git_line."""
    # Synthetic file where target resource starts at line 42
    padding = ["# padding line\n"] * 41  # lines 1 to 41
    resource_block = [
        'resource "aws_s3_bucket" "financial_records" {\n',  # line 42
        '  bucket = "acme-financial-records-prod"\n',          # line 43
        '}\n',                                                 # line 44
    ]
    file_content = "".join(padding + resource_block)

    start_line, end_line = FuzzyASTMatcher.locate_resource(
        file_content=file_content,
        resource_type="aws_s3_bucket",
        resource_name="financial_records",
    )

    assert start_line == 42
    assert end_line == 44

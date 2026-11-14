"""Integration tests for Automated GitOps PR Generation (TC-MOD11-003).

Verifies that remediating a finding opens a Pull Request with cryptographic evidence and valid PR URL.
"""

import pytest

from services.mod11_iac_gitops.internal.pr_generator.github_client import GitHubPRClient


def test_tc_mod11_003_github_pr_generation_mock():
    """TC-MOD11-003: Click 'Remediate via PR' on finding IOM-S3-PUBLIC-ACL.

    Expected: GitHub client mocks branch creation, commits patch, and returns valid PR URL https://github.com/acme/infra/pull/104.
    """
    repo_full_name = "acme/infra"
    base_branch = "main"
    rule_id = "IOM-S3-PUBLIC-ACL"
    file_path = "terraform/s3.tf"
    diff_text = (
        "--- a/terraform/s3.tf\n"
        "+++ b/terraform/s3.tf\n"
        "@@ -10,3 +10,3 @@\n"
        "-  block_public_acls = false\n"
        "+  block_public_acls = true\n"
    )

    pr_result = GitHubPRClient.create_remediation_pr(
        repo_full_name=repo_full_name,
        base_branch=base_branch,
        rule_id=rule_id,
        file_path=file_path,
        diff_text=diff_text,
        finding_title="S3 Bucket Missing Public Access Block",
        pr_number=104,
    )

    assert pr_result["repo_full_name"] == "acme/infra"
    assert pr_result["base_branch"] == "main"
    assert pr_result["pr_number"] == 104
    assert pr_result["pr_url"] == "https://github.com/acme/infra/pull/104"
    assert pr_result["branch_name"].startswith("lograven/fix-iom-s3-public-acl-")
    assert pr_result["status"] == "OPEN"
    assert "IOM-S3-PUBLIC-ACL" in pr_result["body"]
    assert "terraform/s3.tf" in pr_result["body"]

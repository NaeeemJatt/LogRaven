"""Code-to-Cloud Tag Correlator (PRD-MOD-11 / TC-MOD11-002).

Extracts and correlates Git repository, file path, commit SHA, and line numbers
from runtime cloud resource tags applied by Terraform / CI-CD pipelines.
"""

from typing import Any, Dict, Optional


class TagCorrelator:
    """Extracts GitOps source lineage from runtime cloud resource tags."""

    REPO_TAG_KEYS = ("git_repo", "repository", "git:repo", "iac_repo", "repo")
    FILE_TAG_KEYS = ("git_file", "iac_file", "git:file", "file_path", "terraform_file")
    COMMIT_TAG_KEYS = ("git_commit", "commit_sha", "git:commit", "git_sha")
    LINE_TAG_KEYS = ("git_line", "line_number", "git:line", "line")

    @classmethod
    def extract_git_metadata(cls, tags: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts normalized Git metadata from asset tags."""
        tags_lower = {k.lower(): str(v) for k, v in tags.items()}

        repo_full_name = None
        for k in cls.REPO_TAG_KEYS:
            if k in tags_lower:
                repo_full_name = tags_lower[k]
                break

        file_path = None
        for k in cls.FILE_TAG_KEYS:
            if k in tags_lower:
                file_path = tags_lower[k]
                break

        commit_sha = None
        for k in cls.COMMIT_TAG_KEYS:
            if k in tags_lower:
                commit_sha = tags_lower[k]
                break

        line_number = None
        for k in cls.LINE_TAG_KEYS:
            if k in tags_lower:
                try:
                    line_number = int(tags_lower[k])
                except ValueError:
                    pass
                break

        has_lineage = bool(repo_full_name and file_path)

        return {
            "has_lineage": has_lineage,
            "repo_full_name": repo_full_name,
            "file_path": file_path,
            "commit_sha": commit_sha or "HEAD",
            "line_number": line_number,
        }

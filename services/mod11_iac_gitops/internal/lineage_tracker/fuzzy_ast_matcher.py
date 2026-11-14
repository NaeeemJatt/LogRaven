"""Fuzzy AST Lineage Matcher (PRD-MOD-11 / TC-MOD11-002).

Scans Terraform HCL source files to locate the exact definition line of a resource block.
"""

import re
from typing import Any, Dict, Optional, Tuple


class FuzzyASTMatcher:
    """Matches cloud asset names and types to specific line numbers in IaC source files."""

    @classmethod
    def locate_resource(
        cls,
        file_content: str,
        resource_type: str,
        resource_name: Optional[str] = None,
    ) -> Tuple[int, int]:
        """Returns (start_line, end_line) of the resource block in file_content (1-indexed)."""
        lines = file_content.splitlines()

        if resource_name:
            pattern = re.compile(
                rf'^\s*resource\s+"{re.escape(resource_type)}"\s+"{re.escape(resource_name)}"\s*{{'
            )
        else:
            pattern = re.compile(rf'^\s*resource\s+"{re.escape(resource_type)}"\s+"[^"]+"\s*{{')

        start_line = -1
        end_line = -1
        brace_count = 0
        in_block = False

        for idx, line in enumerate(lines, start=1):
            if not in_block and pattern.search(line):
                start_line = idx
                in_block = True
                brace_count += line.count("{") - line.count("}")
                continue

            if in_block:
                brace_count += line.count("{") - line.count("}")
                if brace_count <= 0:
                    end_line = idx
                    break

        if start_line != -1 and end_line == -1:
            end_line = len(lines)

        return (start_line, end_line) if start_line != -1 else (1, len(lines))

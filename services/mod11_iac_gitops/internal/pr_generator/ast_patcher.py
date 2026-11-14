"""Terraform HCL & IaC AST Patcher (PRD-MOD-11 / TC-MOD11-001).

Performs surgical, comment-preserving, indentation-preserving modifications on Terraform HCL2 source files
and generates clean unified git diffs ready for automated Pull Requests.
"""

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple


class ASTPatcher:
    """Surgically modifies Terraform HCL attributes while strictly preserving comments and indentation."""

    @classmethod
    def patch_attribute(
        cls,
        hcl_content: str,
        attribute: str,
        new_value: Any,
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Patches an HCL attribute (e.g. flipping block_public_acls = false to true).

        Returns:
            Dict containing original_content, patched_content, diff, and modified flag.
        """
        raw_lines = hcl_content.splitlines()
        modified = False
        patched_lines: List[str] = []

        # Format target value as HCL literal
        if isinstance(new_value, bool):
            val_str = "true" if new_value else "false"
        elif isinstance(new_value, (int, float)):
            val_str = str(new_value)
        elif isinstance(new_value, list):
            items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in new_value)
            val_str = f"[{items}]"
        else:
            val_str = f'"{new_value}"'

        # Regex matching attribute assignment with any whitespace and comments preserved
        attr_regex = re.compile(
            rf"^(\s*{re.escape(attribute)}\s*=\s*)([^\s#]+)(.*)$"
        )

        in_target_block = True
        if resource_type and resource_name:
            in_target_block = False

        block_header_regex = re.compile(
            rf'^\s*resource\s+"{re.escape(resource_type or "")}"\s+"{re.escape(resource_name or "")}"\s*{{'
        )

        for line in raw_lines:
            if not in_target_block and block_header_regex.search(line):
                in_target_block = True
                patched_lines.append(line)
                continue

            if in_target_block:
                m = attr_regex.match(line)
                if m:
                    prefix = m.group(1)  # Indentation and attribute name + " = "
                    suffix = m.group(3)  # Inline comments or trailing whitespace
                    new_line = f"{prefix}{val_str}{suffix}"
                    patched_lines.append(new_line)
                    modified = True
                    continue

            patched_lines.append(line)

        patched_content = "\n".join(patched_lines)
        if hcl_content.endswith("\n"):
            patched_content += "\n"

        # Generate standard unified diff
        diff_lines = list(
            difflib.unified_diff(
                [l + "\n" for l in raw_lines],
                [l + "\n" for l in patched_lines],
                fromfile="a/terraform/main.tf",
                tofile="b/terraform/main.tf",
            )
        )
        diff_text = "".join(diff_lines)

        return {
            "attribute": attribute,
            "new_value": new_value,
            "modified": modified,
            "original_content": hcl_content,
            "patched_content": patched_content,
            "diff": diff_text,
        }

"""Visual-to-Rego Compiler (PRD-MOD-12 / TC-MOD12-001).

Compiles visual condition trees into valid, executable Open Policy Agent (OPA) Rego code.
"""

from typing import Any, Dict, List, Optional
import json


class RegoCompiler:
    """Compiles visual rule conditions into Open Policy Agent (OPA) Rego policy code."""

    @classmethod
    def compile_rule(
        cls,
        rule_id: str,
        resource_type: str,
        conditions: List[Dict[str, Any]],
        message: Optional[str] = None,
        package_name: str = "lograven.rules.custom",
    ) -> str:
        """Translates visual AST conditions into a standard OPA Rego deny rule.

        Example output for S3 bucket versioning check:
            package lograven.rules.custom

            default allow = true

            deny[msg] {
                input.resource_type == "aws_s3_bucket"
                input.versioning.status != "Enabled"
                msg := "S3 bucket versioning is not enabled."
            }
        """
        lines: List[str] = []
        lines.append(f"package {package_name}")
        lines.append("")
        lines.append("default allow = true")
        lines.append("")
        lines.append("deny[msg] {")

        # 1. Resource type match
        if resource_type and resource_type != "*":
            lines.append(f'    input.resource_type == "{resource_type}"')

        # 2. Iterate conditions
        for cond in conditions:
            field = cond.get("field", "").strip()
            operator = cond.get("operator", "==").strip()
            val = cond.get("value")

            # Prefix field with input. if not already present
            full_field = f"input.{field}" if not field.startswith("input.") else field
            val_repr = cls._format_value(val)

            if operator in ("==", "!=", ">", "<", ">=", "<="):
                lines.append(f"    {full_field} {operator} {val_repr}")
            elif operator == "contains":
                lines.append(f"    contains({full_field}, {val_repr})")
            elif operator == "in":
                lines.append(f"    {val_repr} in {full_field}")
            else:
                lines.append(f"    {full_field} == {val_repr}")

        # 3. Denial message assignment
        denial_msg = message or f"Resource violates policy {rule_id}"
        lines.append(f'    msg := "{denial_msg}"')
        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_value(val: Any) -> str:
        """Formats python primitives into Rego literals."""
        if isinstance(val, bool):
            return "true" if val else "false"
        elif isinstance(val, (int, float)):
            return str(val)
        elif isinstance(val, list):
            items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in val)
            return f"[{items}]"
        elif isinstance(val, str):
            return f'"{val}"'
        else:
            return json.dumps(val)

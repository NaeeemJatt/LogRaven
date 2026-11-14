"""MCP Tool Scope & Permission Analyzer (PRD-MOD-09 / TC-MOD9-002).

Audits tool definitions advertised by Model Context Protocol (MCP) endpoints
against MITRE ATT&CK for AI / execution capabilities (Shell, SQL, FS write).
"""

from typing import Any, Dict, List, Set

SHELL_INDICATORS: Set[str] = {
    "bash", "shell", "sh", "terminal", "execute_command", "run_command",
    "execute_bash", "cmd", "powershell", "exec", "eval", "cli_execute"
}

SQL_INDICATORS: Set[str] = {
    "sql", "query", "sql_query", "execute_sql", "run_sql", "database_write",
    "db_query", "raw_query", "postgres_query", "mysql_query"
}

FS_WRITE_INDICATORS: Set[str] = {
    "write_file", "delete_file", "remove_file", "put_file", "overwrite_file",
    "create_file", "append_file"
}


class ToolScopeAnalyzer:
    """Classifies risk level of MCP tools based on advertised interfaces and schemas."""

    @classmethod
    def analyze_tools(cls, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes a list of MCP tool specifications."""
        findings: List[Dict[str, Any]] = []
        has_shell = False
        has_sql = False
        has_fs_write = False

        for tool in tools:
            name = str(tool.get("name", "")).lower().strip()
            desc = str(tool.get("description", "")).lower().strip()
            params = tool.get("inputSchema", {}) or tool.get("parameters", {})

            # Shell execution check
            if any(ind in name for ind in SHELL_INDICATORS) or "command line" in desc or "bash script" in desc:
                has_shell = True
                findings.append({
                    "tool_name": tool.get("name"),
                    "finding_code": "HIGH_RISK_MCP_TOOL_SHELL",
                    "severity": "HIGH",
                    "description": f"Tool '{tool.get('name')}' grants arbitrary operating system shell execution to LLM agent.",
                })

            # Arbitrary SQL query check
            elif any(ind in name for ind in SQL_INDICATORS) or "run sql" in desc or "raw query" in desc:
                has_sql = True
                findings.append({
                    "tool_name": tool.get("name"),
                    "finding_code": "HIGH_RISK_MCP_TOOL_SQL",
                    "severity": "HIGH",
                    "description": f"Tool '{tool.get('name')}' grants arbitrary SQL execution to LLM agent.",
                })

            # File system write check
            elif any(ind in name for ind in FS_WRITE_INDICATORS) or "write to file" in desc:
                has_fs_write = True
                findings.append({
                    "tool_name": tool.get("name"),
                    "finding_code": "HIGH_RISK_MCP_TOOL_FS_WRITE",
                    "severity": "MEDIUM",
                    "description": f"Tool '{tool.get('name')}' grants file modification/deletion privileges.",
                })

        has_high_risk = has_shell or has_sql

        return {
            "total_tools": len(tools),
            "has_high_risk_tools": has_high_risk,
            "has_shell": has_shell,
            "has_sql": has_sql,
            "has_fs_write": has_fs_write,
            "findings": findings,
        }

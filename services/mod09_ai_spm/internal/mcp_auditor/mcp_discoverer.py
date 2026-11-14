"""Model Context Protocol (MCP) Server Discoverer & Auditor (PRD-MOD-09 / TC-MOD9-002)."""

from typing import Any, Dict, List, Optional

from services.mod09_ai_spm.internal.mcp_auditor.auth_verifier import MCPAuthVerifier
from services.mod09_ai_spm.internal.mcp_auditor.tool_scope_analyzer import ToolScopeAnalyzer


class MCPAuditor:
    """Discovers, audits, and grades risk posture of Model Context Protocol (MCP) instances."""

    @classmethod
    def audit_server(
        cls,
        server_urn: str,
        endpoint_url: str,
        tools: List[Dict[str, Any]],
        auth_enforced: bool = False,
        network_binding: str = "0.0.0.0",
    ) -> Dict[str, Any]:
        """Conducts a comprehensive audit on an MCP server instance."""
        auth_eval = MCPAuthVerifier.evaluate_endpoint(
            endpoint_url=endpoint_url,
            auth_header_present=auth_enforced,
            requires_mtls=False,
            network_binding=network_binding,
        )

        tool_eval = ToolScopeAnalyzer.analyze_tools(tools)

        all_findings = []
        all_findings.extend(auth_eval.get("findings", []))
        all_findings.extend(tool_eval.get("findings", []))

        # Overall severity
        has_critical = any(f.get("finding_code") == "CRITICAL_EXPOSED_MCP_SERVER" for f in all_findings)
        has_high = any(f.get("severity") == "HIGH" for f in all_findings)

        if has_critical:
            overall_severity = "CRITICAL"
        elif has_high:
            overall_severity = "HIGH"
        elif all_findings:
            overall_severity = "MEDIUM"
        else:
            overall_severity = "LOW"

        return {
            "server_urn": server_urn,
            "endpoint_url": endpoint_url,
            "is_publicly_exposed": auth_eval.get("is_publicly_exposed", False),
            "auth_enforced": auth_eval.get("auth_enforced", False),
            "available_tools": tools,
            "has_high_risk_tools": tool_eval.get("has_high_risk_tools", False),
            "findings": all_findings,
            "overall_severity": overall_severity,
        }

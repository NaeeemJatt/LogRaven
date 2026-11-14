"""Integration tests for Model Context Protocol (MCP) Governance (TC-MOD9-002).

Audits MCP servers for public exposure, authentication bypass, and hazardous tool scopes (Shell, SQL).
"""

import pytest

from services.mod09_ai_spm.internal.mcp_auditor.mcp_discoverer import MCPAuditor


def test_tc_mod9_002_exposed_mcp_server_with_shell_tools():
    """TC-MOD9-002: Deploy mock MCP server exposing read_file and execute_bash with zero authentication on public IP.

    Expected: Auditor flags CRITICAL_EXPOSED_MCP_SERVER and HIGH_RISK_MCP_TOOL_SHELL; creates urgent alert.
    """
    server_urn = "urn:lograven:mcp:us-east-1:112233445566:server/agent-executor"
    public_endpoint = "http://203.0.113.45:8080/mcp/sse"

    # Mock tools exposing read_file and execute_bash
    mock_tools = [
        {
            "name": "read_file",
            "description": "Reads contents of a file on the local host",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        {
            "name": "execute_bash",
            "description": "Executes an arbitrary bash script or shell command in container",
            "inputSchema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    ]

    # Run auditor on public endpoint without authentication
    audit_res = MCPAuditor.audit_server(
        server_urn=server_urn,
        endpoint_url=public_endpoint,
        tools=mock_tools,
        auth_enforced=False,
        network_binding="0.0.0.0",
    )

    # Verify exposure & auth flags
    assert audit_res["is_publicly_exposed"] is True
    assert audit_res["auth_enforced"] is False
    assert audit_res["has_high_risk_tools"] is True
    assert audit_res["overall_severity"] == "CRITICAL"

    finding_codes = [f["finding_code"] for f in audit_res["findings"]]
    assert "CRITICAL_EXPOSED_MCP_SERVER" in finding_codes
    assert "HIGH_RISK_MCP_TOOL_SHELL" in finding_codes


def test_secure_private_mcp_server():
    """Verifies that private, authenticated MCP server with benign tools passes audit."""
    server_urn = "urn:lograven:mcp:us-west-2:112233445566:server/rag-retriever"
    private_endpoint = "http://rag-service.corp.internal:8000/sse"

    benign_tools = [
        {
            "name": "search_docs",
            "description": "Performs cosine similarity search against indexed corporate documentation",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }
    ]

    audit_res = MCPAuditor.audit_server(
        server_urn=server_urn,
        endpoint_url=private_endpoint,
        tools=benign_tools,
        auth_enforced=True,
        network_binding="10.0.1.15",
    )

    assert audit_res["is_publicly_exposed"] is False
    assert audit_res["auth_enforced"] is True
    assert audit_res["has_high_risk_tools"] is False
    assert audit_res["overall_severity"] == "LOW"
    assert len(audit_res["findings"]) == 0

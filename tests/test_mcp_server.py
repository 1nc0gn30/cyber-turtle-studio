"""Tests for Model Context Protocol (MCP) Server and JSON-RPC 2.0 protocol handlers."""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest
from cyber_turtle_studio.mcp_server import MCPServer


@pytest.fixture
def mcp_server() -> MCPServer:
    """Provide fresh MCPServer instance."""
    return MCPServer()


def test_mcp_server_initialize(mcp_server: MCPServer):
    """Verify MCP initialize lifecycle handshake."""
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
            "capabilities": {},
        },
    }
    response = mcp_server.handle_jsonrpc_request(init_request)
    assert response is not None
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    result = response["result"]
    assert result["serverInfo"]["name"] == "cyber-turtle-studio"
    assert "capabilities" in result


def test_mcp_list_tools(mcp_server: MCPServer):
    """Verify listing registered MCP tools."""
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    resp = mcp_server.handle_jsonrpc_request(req)
    assert resp is not None
    tools = resp["result"]["tools"]
    tool_names = {t["name"] for t in tools}

    assert "turtle_execute_logo" in tool_names
    assert "turtle_generate_lsystem" in tool_names
    assert "turtle_export_svg" in tool_names
    assert "turtle_export_gcode" in tool_names
    assert "turtle_presets" in tool_names
    assert "turtle_diagnostics" in tool_names


def test_mcp_tool_execute_logo(mcp_server: MCPServer):
    """Verify executing Logo DSL via MCP tool call."""
    res = mcp_server.handle_tool_call(
        "turtle_execute_logo",
        {"script": "repeat 4 [ fd 50 rt 90 ]", "theme": "cyber_matrix"},
    )
    assert "content" in res
    assert res.get("isError") is not True
    text = res["content"][0]["text"]
    assert "<svg" in text or "segments" in text.lower() or "Drawing" in text


def test_mcp_tool_generate_lsystem(mcp_server: MCPServer):
    """Verify generating L-System fractal via MCP tool call."""
    res = mcp_server.handle_tool_call(
        "turtle_generate_lsystem",
        {
            "axiom": "F--F--F",
            "rules": {"F": "F+F--F+F"},
            "angle": 60.0,
            "iterations": 2,
        },
    )
    assert "content" in res
    assert res.get("isError") is not True


def test_mcp_tool_presets_and_diagnostics(mcp_server: MCPServer):
    """Verify presets list and diagnostics tools."""
    p_res = mcp_server.handle_tool_call("turtle_presets", {})
    assert "content" in p_res
    assert len(p_res["content"]) > 0

    d_res = mcp_server.handle_tool_call("turtle_diagnostics", {})
    assert "content" in d_res
    assert "platform" in d_res["content"][0]["text"].lower() or "version" in d_res["content"][0]["text"].lower()


def test_mcp_resources_and_prompts(mcp_server: MCPServer):
    """Verify registered resources (grammar guide, presets) and prompts."""
    # List resources
    res_list_req = {"jsonrpc": "2.0", "id": 10, "method": "resources/list", "params": {}}
    res_resp = mcp_server.handle_jsonrpc_request(res_list_req)
    assert "resources" in res_resp["result"]

    # Read grammar guide resource
    read_guide = mcp_server.handle_resource_read("turtle://grammar-guide")
    assert "contents" in read_guide
    assert "Logo" in read_guide["contents"][0]["text"]

    # List prompts
    prompt_list_req = {"jsonrpc": "2.0", "id": 11, "method": "prompts/list", "params": {}}
    prompt_resp = mcp_server.handle_jsonrpc_request(prompt_list_req)
    assert "prompts" in prompt_resp["result"]

    # Get prompt
    prompt_get = mcp_server.handle_prompt_get("turtle_create_fractal", {"style": "geometric"})
    assert "messages" in prompt_get

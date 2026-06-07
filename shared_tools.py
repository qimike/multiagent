"""Shared custom tool(s) available to every domain agent.

One MCP server (`shared`) bundling tools that are not domain-specific. Each domain
agent receives this server in addition to its own. Tool names follow the SDK
convention ``mcp__<server-name>__<tool-name>`` and must be listed in
``allowed_tools`` for the agent to call them.

The implementation here is a clearly-marked TODO placeholder — wire it to your real
policy store when ready.
"""

from __future__ import annotations

from claude_agent_sdk import create_sdk_mcp_server, tool

SERVER_NAME = "shared"


@tool(
    "policy_version",
    "Return the active conformance policy version and its effective date so a "
    "review can record which ruleset it was assessed against. Takes no arguments.",
    {},
)
async def policy_version(args: dict) -> dict:
    # TODO: replace with a real lookup against the governance policy registry.
    return {
        "content": [
            {
                "type": "text",
                "text": "[STUB] Conformance policy version 2026.1 (effective 2026-01-01).",
            }
        ]
    }


# The MCP server bundling the shared tool(s).
MCP_SERVER = create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=[policy_version])

# Fully-qualified tool names for allowed_tools wiring.
TOOL_NAMES = [f"mcp__{SERVER_NAME}__policy_version"]

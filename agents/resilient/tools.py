"""Resilient-domain custom tools.

Bundled into one MCP server (`resilient`). Tool names follow the SDK convention
``mcp__resilient__<tool-name>`` and must be listed in ``allowed_tools``.

The implementation is a clearly-marked TODO placeholder. ``call_api`` is a generic
example of an outbound integration; it imports ``httpx`` (a dependency in
pyproject.toml) but
does NOT make a live request by default, so an unattended governance run never makes
surprise network calls. Enable the real call where marked when you wire it up.

TODO: for the Resilient domain, replace/extend this with tools that probe resilience
posture — e.g. SLA/SLO targets, health-check & failover status, backup/DR readiness,
or alerting coverage — rather than the generic ``call_api`` placeholder below.
"""

from __future__ import annotations

import httpx  # noqa: F401  (used by the real implementation; see TODO below)
from claude_agent_sdk import create_sdk_mcp_server, tool

SERVER_NAME = "resilient"


@tool(
    "call_api",
    "Generic example tool: probe an external HTTP endpoint (e.g., a system the "
    "design depends on) and return a short status summary. Use when an endpoint's "
    "status would change your assessment.",
    {"url": str},
)
async def call_api(args: dict) -> dict:
    url = args.get("url", "")
    # TODO: replace this stub with a real request, e.g.:
    #     async with httpx.AsyncClient(timeout=10) as client:
    #         resp = await client.get(url)
    #         text = f"GET {url} -> {resp.status_code}"
    # Left disabled so unattended runs make no outbound calls.
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"[STUB] Outbound calls are disabled in this build, so I did not "
                    f"probe '{url}'. Treat its status as 'unknown'."
                ),
            }
        ]
    }


MCP_SERVER = create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=[call_api])

TOOL_NAMES = [f"mcp__{SERVER_NAME}__call_api"]

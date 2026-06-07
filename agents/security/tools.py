"""Security-domain custom tools.

Bundled into one MCP server (`security`). Tool names follow the SDK convention
``mcp__security__<tool-name>`` and must be listed in ``allowed_tools``.

All implementations are clearly-marked TODO placeholders — wire them to a real
secrets vault when ready.
"""

from __future__ import annotations

from claude_agent_sdk import create_sdk_mcp_server, tool

SERVER_NAME = "security"


@tool(
    "check_secret_in_vault",
    "Check whether a named secret (DB credential, API key, token) is stored in the "
    "approved secrets vault, and report its rotation status. Use this to verify "
    "secrets-management claims instead of assuming.",
    {"secret_name": str},
)
async def check_secret_in_vault(args: dict) -> dict:
    secret_name = args.get("secret_name", "")
    # TODO: replace with a real vault lookup (HashiCorp Vault / cloud KMS / Secrets Manager).
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"[STUB] No live vault is configured, so I cannot confirm "
                    f"'{secret_name}' is vaulted or how it is rotated. Treat as "
                    "'unknown' and rely on what the document states."
                ),
            }
        ]
    }


MCP_SERVER = create_sdk_mcp_server(
    name=SERVER_NAME, version="1.0.0", tools=[check_secret_in_vault]
)

TOOL_NAMES = [f"mcp__{SERVER_NAME}__check_secret_in_vault"]

"""Data-domain custom tools.

Bundled into one MCP server (`data`). Tool names follow the SDK convention
``mcp__data__<tool-name>`` and must be listed in ``allowed_tools``.

All implementations are clearly-marked TODO placeholders — wire them to a real
catalog / data platform when ready.
"""

from __future__ import annotations

from claude_agent_sdk import create_sdk_mcp_server, tool

SERVER_NAME = "data"


@tool(
    "check_pii_classification",
    "Look up whether a table/dataset holding personal data has a documented PII "
    "classification on record. Use this to verify data-classification claims.",
    {"table": str},
)
async def check_pii_classification(args: dict) -> dict:
    table = args.get("table", "")
    # TODO: replace with a real data-catalog lookup (e.g., a governance catalog API).
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"[STUB] No live data catalog is configured, so I cannot confirm a "
                    f"PII classification for '{table}'. Treat as 'unknown' and rely on "
                    "what the document states."
                ),
            }
        ]
    }


@tool(
    "check_record_exists",
    "Check whether a specific record/profile id exists in the data platform. Use "
    "this before relying on a record the document references.",
    {"record_id": str},
)
async def check_record_exists(args: dict) -> dict:
    record_id = args.get("record_id", "")
    # TODO: replace with a real existence check against the warehouse / store.
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"[STUB] No live data store is configured, so I cannot confirm "
                    f"record '{record_id}' exists. Treat as 'unknown'."
                ),
            }
        ]
    }


MCP_SERVER = create_sdk_mcp_server(
    name=SERVER_NAME,
    version="1.0.0",
    tools=[check_pii_classification, check_record_exists],
)

TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__check_pii_classification",
    f"mcp__{SERVER_NAME}__check_record_exists",
]

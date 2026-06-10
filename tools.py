"""The shared governance MCP server and its single tool.

ONE shared in-process MCP server (`governance`) is used by every agent — there is no
per-domain server. It exposes exactly one tool:

  get_guideline(domain, version) -> versioned guideline + examples

`get_guideline` is the ONLY governance MCP tool. It abstracts away where guidelines
physically live (local folders, Git, SharePoint, Confluence, DocuFind, …) so agents never
need to know the storage location. Governance content lives in guidelines/, not in skills.
"""

from __future__ import annotations

from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool

from domains import DOMAINS

ROOT = Path(__file__).parent
GUIDELINES_DIR = ROOT / "guidelines"
SERVER_NAME = "governance"

DEFAULT_VERSION = "v1"


@tool(
    "get_guideline",
    "Load a domain's versioned governance guideline AND examples. 'domain' is one of "
    "data_movement, security, resilience. 'version' defaults to v1. Use both files.",
    {"domain": str, "version": str},
)
async def get_guideline(args: dict) -> dict:
    domain = (args.get("domain") or "").strip().lower()
    version = (args.get("version") or DEFAULT_VERSION).strip().lower()
    if domain not in DOMAINS:
        return {
            "content": [
                {"type": "text", "text": f"Unknown domain '{domain}'. Valid: {', '.join(DOMAINS)}."}
            ]
        }
    base = GUIDELINES_DIR / domain / version
    guideline = base / "guideline.md"
    examples = base / "examples.md"
    if not guideline.exists():
        return {
            "content": [
                {"type": "text", "text": f"No guideline for {domain}/{version} at {base}."}
            ]
        }
    g = guideline.read_text(encoding="utf-8")
    e = examples.read_text(encoding="utf-8") if examples.exists() else "(no examples.md)"
    text = (
        f"domain={domain} version={version}\n\n"
        f"===== GUIDELINE ({domain}/{version}) =====\n{g}\n\n"
        f"===== EXAMPLES ({domain}/{version}) =====\n{e}"
    )
    return {"content": [{"type": "text", "text": text}]}


MCP_SERVER = create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=[get_guideline])

TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__get_guideline",
]

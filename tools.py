"""The two governance-evaluation tools, exposed as one in-process MCP server.

Per the SAD governance framework the evaluators have EXACTLY two tools:

  1. get_guideline(domain)                 -> that domain's guideline + examples
  2. find_evidence(markdown_document, q)   -> supporting evidence inside the SAD

Everything else (PII detection, secret scanning, user/email lookup, mock policy
databases, external compliance services) has been removed.
"""

from __future__ import annotations

import re
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool

ROOT = Path(__file__).parent
GUIDELINES_DIR = ROOT / "guidelines"
SERVER_NAME = "governance"

VALID_DOMAINS = ("data_movement", "security", "resilience")


@tool(
    "get_guideline",
    "Load a domain's governance guideline AND examples. 'domain' must be one of: "
    "data_movement, security, resilience. Use both the guideline and the examples "
    "when evaluating.",
    {"domain": str},
)
async def get_guideline(args: dict) -> dict:
    domain = (args.get("domain") or "").strip().lower()
    if domain not in VALID_DOMAINS:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown domain '{domain}'. Valid domains: {', '.join(VALID_DOMAINS)}.",
                }
            ]
        }
    base = GUIDELINES_DIR / domain
    guideline = base / "guideline.md"
    examples = base / "examples.md"
    g = guideline.read_text(encoding="utf-8") if guideline.exists() else "(no guideline.md found)"
    e = examples.read_text(encoding="utf-8") if examples.exists() else "(no examples.md found)"
    text = (
        f"===== GUIDELINE: {domain} =====\n{g}\n\n"
        f"===== EXAMPLES: {domain} =====\n{e}"
    )
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "find_evidence",
    "Locate supporting evidence inside a SAD Markdown document. Returns each match "
    "with its section heading, line number, and the evidence text. Pass the full SAD "
    "Markdown as 'markdown_document' and a search term as 'query'.",
    {"markdown_document": str, "query": str},
)
async def find_evidence(args: dict) -> dict:
    md = args.get("markdown_document") or ""
    query = (args.get("query") or "").strip()
    if not query:
        return {"content": [{"type": "text", "text": "No query provided."}]}

    matches: list[dict] = []
    heading = "(preamble)"
    for i, line in enumerate(md.splitlines(), start=1):
        if re.match(r"^#{1,6}\s+", line):
            heading = line.lstrip("# ").strip()
        if query.lower() in line.lower() and not re.match(r"^#{1,6}\s+", line):
            matches.append({"section": heading, "line": i, "evidence": line.strip()})

    if not matches:
        return {"content": [{"type": "text", "text": f"No evidence found for '{query}'."}]}

    rendered = "\n".join(
        f'- section "{m["section"]}" (line {m["line"]}): {m["evidence"]}' for m in matches
    )
    return {"content": [{"type": "text", "text": f"Evidence for '{query}':\n{rendered}"}]}


MCP_SERVER = create_sdk_mcp_server(
    name=SERVER_NAME, version="1.0.0", tools=[get_guideline, find_evidence]
)

TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__get_guideline",
    f"mcp__{SERVER_NAME}__find_evidence",
]

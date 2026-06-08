"""The shared governance MCP server and its two tools.

ONE shared in-process MCP server (`governance`) is used by every agent — there is no
per-domain server. It exposes exactly two tools:

  1. get_guideline(domain, version)        -> versioned guideline + examples (governance
                                               content lives in guidelines/, not in skills)
  2. find_evidence(markdown_document, query) -> BM25 (semantic-ranked) evidence with
                                               provenance (section + line_range + confidence)
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool

import parser

ROOT = Path(__file__).parent
GUIDELINES_DIR = ROOT / "guidelines"
SERVER_NAME = "governance"

DEFAULT_VERSION = "v1"


# ---------------------------------------------------------------------------
# Tool 1 — versioned guideline retrieval
# ---------------------------------------------------------------------------
@tool(
    "get_guideline",
    "Load a domain's versioned governance guideline AND examples. 'domain' is one of "
    "data_movement, security, resilience. 'version' defaults to v1. Use both files.",
    {"domain": str, "version": str},
)
async def get_guideline(args: dict) -> dict:
    domain = (args.get("domain") or "").strip().lower()
    version = (args.get("version") or DEFAULT_VERSION).strip().lower()
    if domain not in parser.DOMAINS:
        return {
            "content": [
                {"type": "text", "text": f"Unknown domain '{domain}'. Valid: {', '.join(parser.DOMAINS)}."}
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


# ---------------------------------------------------------------------------
# Tool 2 — BM25 evidence retrieval (replaces keyword matching)
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _bm25_rank(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Return a BM25 score per doc for the query."""
    tok_docs = [_tokenize(d) for d in docs]
    lengths = [len(d) for d in tok_docs]
    avgdl = (sum(lengths) / len(lengths)) if lengths else 0.0
    n = len(tok_docs)
    df: Counter = Counter()
    for d in tok_docs:
        for term in set(d):
            df[term] += 1
    q_terms = [t for t in set(_tokenize(query)) if t]
    scores: list[float] = []
    for i, d in enumerate(tok_docs):
        tf = Counter(d)
        dl = lengths[i] or 1
        score = 0.0
        for t in q_terms:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            freq = tf[t]
            denom = freq + k1 * (1 - b + b * dl / (avgdl or 1))
            score += idf * (freq * (k1 + 1)) / denom
        scores.append(score)
    return scores


def _best_snippet(section_body: str, line_start: int, query: str) -> tuple[str, str]:
    """Pick the line(s) within a section most relevant to the query. Returns
    (evidence_text, line_range) with absolute (1-based) line numbers."""
    q = set(_tokenize(query))
    lines = section_body.split("\n")
    best_i, best_overlap = 0, -1
    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+", line):
            continue
        overlap = len(q & set(_tokenize(line)))
        if overlap > best_overlap:
            best_overlap, best_i = overlap, i
    abs_line = line_start + best_i
    return lines[best_i].strip(), f"{abs_line}-{abs_line}"


@tool(
    "find_evidence",
    "Optional Evidence Locator (fallback utility) — evidence is primarily generated "
    "directly by evaluator reasoning; this tool is NOT the primary mechanism. It locates "
    "text in a SAD via BM25 ranking over sections (e.g. to confirm a line number). Pass "
    "the full SAD Markdown as 'markdown_document' and a query; returns top matches with "
    "evidence_text, section, line_range, and a confidence score.",
    {"markdown_document": str, "query": str},
)
async def find_evidence(args: dict) -> dict:
    md = args.get("markdown_document") or ""
    query = (args.get("query") or "").strip()
    if not query:
        return {"content": [{"type": "text", "text": "No query provided."}]}

    sections = [s for s in parser.parse_sections(md) if s.body.strip()]
    if not sections:
        return {"content": [{"type": "text", "text": "No sections to search."}]}

    scores = _bm25_rank(query, [s.body for s in sections])
    ranked = sorted(zip(sections, scores), key=lambda x: x[1], reverse=True)
    top = [(s, sc) for s, sc in ranked if sc > 0][:3]
    if not top:
        return {"content": [{"type": "text", "text": f"No evidence found for '{query}'."}]}

    max_score = top[0][1] or 1.0
    results = []
    for s, sc in top:
        text, line_range = _best_snippet(s.body, s.line_start, query)
        results.append(
            {
                "evidence_text": text,
                "section": s.heading,
                "line_range": line_range,
                "confidence": round(sc / max_score, 2),
            }
        )
    rendered = "\n".join(
        f'- [{r["confidence"]}] section "{r["section"]}" ({r["line_range"]}): {r["evidence_text"]}'
        for r in results
    )
    return {"content": [{"type": "text", "text": f"BM25 evidence for '{query}':\n{rendered}"}]}


MCP_SERVER = create_sdk_mcp_server(
    name=SERVER_NAME, version="1.0.0", tools=[get_guideline, find_evidence]
)

TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__get_guideline",
    f"mcp__{SERVER_NAME}__find_evidence",
]

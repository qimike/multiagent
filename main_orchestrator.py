"""
Multi-agent document governance pipeline built on the Claude Agent SDK.

The orchestrator is plain Python; each agent is an isolated Claude call. Because
every query() call is its own session (no shared CLAUDE.md, dedicated system
prompt), each agent gets a FRESH context window and cannot see any other agent's
conversation, guidelines, or results — which is exactly the "sub-agents must not
talk to each other" rule from the architecture.

    documents/*.md
       |
       v
   [Cache]  results/<doc>.json + content_hash  (hit -> skip model calls)
       |  (miss / changed / --force)
       v
   [Orchestrator]  read -> split sections -> route by [Tag] (one section -> one agent)
       |  (one isolated query() per owning domain, run in parallel; empty agents skipped)
       +--> Security Agent   (skills + tools)  --\
       +--> Data Agent       (skills + tools)  ---> validate + detect conflicts
       +--> Resilient Agent  (skills + tools)  --/
       |
       v
   [Synthesis Agent] merge -> one report written to results/<doc>.json
       (3 domain results + synthesis + source_file + content_hash)

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python main_orchestrator.py            # batch over documents/*.md, cached
    python main_orchestrator.py --force    # re-test every document
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from agents import (
    DOMAIN_AGENTS,
    SYNTHESIS_MODEL,
    DomainAgent,
    build_domain_system_prompt,
    build_domain_user_prompt,
    build_synthesis_system_prompt,
)
from schema import detect_conflicts, validate_agent_output

ROOT = Path(__file__).parent
DOCUMENTS_DIR = ROOT / "documents"
RESULTS_DIR = ROOT / "results"


# ---------------------------------------------------------------------------
# Orchestrator helpers (deterministic, no LLM)
# ---------------------------------------------------------------------------
def read_markdown_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_markdown_sections(markdown: str) -> list[tuple[str, str]]:
    """Split on level-2 (##) headers. Returns [(heading, body_with_heading), ...]."""
    sections: list[tuple[str, str]] = []
    heading = "Preamble"
    lines: list[str] = []
    for line in markdown.splitlines():
        if re.match(r"^##\s+", line):
            if lines:
                sections.append((heading, "\n".join(lines).strip()))
            heading = line.lstrip("# ").strip()
            lines = [line]
        else:
            lines.append(line)
    if lines:
        sections.append((heading, "\n".join(lines).strip()))
    return [(h, b) for h, b in sections if b]


# Tag-based routing: each `## [Tag] Heading` section is owned by EXACTLY ONE agent.
# Sections with no tag, or a tag that matches no known domain, go to DEFAULT_OWNER
# (and are surfaced in a warning). There is deliberately NO whole-document fallback —
# that would reintroduce the overlap the tag scheme is meant to remove.
TAG_RE = re.compile(r"^\[([^\]]+)\]\s*(.*)$")
DEFAULT_OWNER = "Resilient"


def _domain_by_tag() -> dict[str, str]:
    return {a.domain.lower(): a.domain for a in DOMAIN_AGENTS}


def _strip_tag_from_body(body: str, clean_heading: str) -> str:
    """Rewrite the section's leading `## [Tag] ...` heading line to a clean title so
    the agent never sees the routing tag. No-op for tagless sections (e.g. Preamble)."""
    lines = body.split("\n")
    if lines and re.match(r"^##\s+", lines[0]):
        lines[0] = f"## {clean_heading}"
    return "\n".join(lines)


def routing_plan(sections: list[tuple[str, str]]) -> list[dict]:
    """Resolve the single owner of every section.

    Returns one dict per section: {heading, owner, matched, body}. `matched` is
    False when the section had no valid tag and fell back to DEFAULT_OWNER. `body`
    has the routing tag stripped from its heading line.
    """
    mapping = _domain_by_tag()
    plan: list[dict] = []
    for heading, body in sections:
        m = TAG_RE.match(heading.strip())
        if m and m.group(1).strip().lower() in mapping:
            owner = mapping[m.group(1).strip().lower()]
            clean_heading = m.group(2).strip()
            matched = True
        elif m:  # had a [Tag] but it names no known domain
            owner = DEFAULT_OWNER
            clean_heading = m.group(2).strip()
            matched = False
        else:    # no [Tag] at all
            owner = DEFAULT_OWNER
            clean_heading = heading.strip()
            matched = False
        plan.append(
            {
                "heading": clean_heading,
                "owner": owner,
                "matched": matched,
                "body": _strip_tag_from_body(body, clean_heading),
            }
        )
    return plan


def route_sections(sections: list[tuple[str, str]]) -> dict[str, str]:
    """Group section text by its single owning domain.

    Each section appears in exactly one bucket. Returns {domain: concatenated text};
    a domain that owns no section maps to "" (empty).
    """
    buckets: dict[str, list[str]] = {a.domain: [] for a in DOMAIN_AGENTS}
    for item in routing_plan(sections):
        buckets[item["owner"]].append(item["body"])
    return {domain: "\n\n".join(parts) if parts else "" for domain, parts in buckets.items()}


# ---------------------------------------------------------------------------
# Agent runners (each is an ISOLATED Claude session)
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> dict:
    """Robustly pull a JSON object out of a model response."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


async def _run_isolated_agent(
    system_prompt: str,
    user_prompt: str,
    model: str,
    *,
    allowed_tools: list[str] | None = None,
    mcp_servers: dict | None = None,
    skills: list[str] | None = None,
    setting_sources: list[str] | None = None,
    max_turns: int = 1,
) -> str:
    """Run one isolated agent turn and return its final text.

    Each query() is its own session, so the agent context is fully isolated
    regardless of these knobs. To enable skills, pass setting_sources=["project"]
    (so .claude/skills is discovered) and include "Skill" in allowed_tools. Custom
    tools need their MCP servers in mcp_servers, their mcp__* names in allowed_tools,
    and max_turns > 1 (call -> result -> reason).
    """
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=model,
        allowed_tools=allowed_tools or [],
        mcp_servers=mcp_servers or {},
        skills=skills or [],
        max_turns=max_turns,
        # setting_sources=[] is full isolation (no CLAUDE.md / settings / skills).
        # Domain agents pass ["project"] to discover .claude/skills.
        setting_sources=setting_sources if setting_sources is not None else [],
    )
    result_text = ""
    async for message in query(prompt=user_prompt, options=options):
        if getattr(message, "result", None):
            result_text = message.result
    return result_text


def content_hash(text: str) -> str:
    """Stable short content fingerprint: first 12 hex chars of a sha256 digest."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _error_result(domain: str, reason: str, raw: str = "") -> dict:
    return {
        "domain": domain,
        "status": "NON_COMPLIANT",
        "conformance_score": 0,
        "evidence": [],
        "violations": [],
        "recommendations": [],
        "confidence": 0.0,
        "exceptions": [reason] + ([raw[:500]] if raw else []),
    }


def _not_applicable_result(domain: str) -> dict:
    """Placeholder for an agent that received no sections (so it is never called).

    We include it (rather than omitting the domain) so the synthesis agent and the
    saved report still cover all three domains and the output validates cleanly.
    """
    return {
        "domain": domain,
        "status": "NOT_APPLICABLE",
        "conformance_score": 0,
        "evidence": [],
        "violations": [],
        "recommendations": [],
        "confidence": 0.0,
        "exceptions": ["No sections were routed to this agent."],
    }


async def run_domain_agent(agent: DomainAgent, section_text: str) -> dict:
    guidelines, examples = agent.load_context()
    system_prompt = build_domain_system_prompt(agent, guidelines, examples)
    user_prompt = build_domain_user_prompt(section_text)

    # Skills (discovered via setting_sources=["project"] + the Skill tool) and the
    # domain's custom tools. Tools need multiple turns: call -> result -> reason.
    allowed_tools = ["Skill", *agent.tool_names()]

    try:
        raw = await _run_isolated_agent(
            system_prompt,
            user_prompt,
            agent.model,
            allowed_tools=allowed_tools,
            mcp_servers=agent.tool_servers(),
            skills=agent.skills,
            setting_sources=["project"],
            max_turns=8,
        )
    except Exception as exc:  # orchestrator catches agent/transport errors
        return _error_result(agent.domain, f"Agent call failed: {exc}")

    try:
        data = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_result(agent.domain, f"Unparseable agent output: {exc}", raw)

    errors = validate_agent_output(data)
    if errors:
        data.setdefault("exceptions", [])
        data["exceptions"].extend(f"schema: {e}" for e in errors)
    return data


async def run_synthesis_agent(results: list[dict], conflicts: list[dict]) -> dict:
    system_prompt = build_synthesis_system_prompt()
    user_prompt = (
        "Here are the domain agent results:\n\n"
        + json.dumps(results, indent=2)
        + "\n\nHere are the conflicts the orchestrator detected:\n\n"
        + json.dumps(conflicts, indent=2)
        + "\n\nProduce the final governance report JSON."
    )
    try:
        raw = await _run_isolated_agent(system_prompt, user_prompt, SYNTHESIS_MODEL)
        return _extract_json(raw)
    except Exception as exc:
        return {
            "overall_status": "UNKNOWN",
            "overall_score": 0,
            "error": f"Synthesis failed: {exc}",
            "domain_results": results,
            "conflicts": conflicts,
        }


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        shown = path.relative_to(ROOT)
    except ValueError:
        shown = path
    print(f"  wrote {shown}")


# ---------------------------------------------------------------------------
# Single-document analysis (no caching, no I/O of its own)
# ---------------------------------------------------------------------------
async def analyze_document(text: str) -> dict:
    """Run the full pipeline on one document's text and return the report dict.

    The three domain agents run isolated and in parallel; synthesis is a separate
    isolated call. `source_file`/`content_hash` are added by run_or_get_cached.
    """
    sections = split_markdown_sections(text)
    print(f"  split into {len(sections)} section(s)")

    # Resolve each section's single owner and print the routing summary.
    plan = routing_plan(sections)
    print("  routing (one section -> one agent):")
    fallbacks = [item["heading"] for item in plan if not item["matched"]]
    for item in plan:
        flag = "" if item["matched"] else "   <- no valid [Tag]; DEFAULT_OWNER"
        print(f"    [{item['owner']}] {item['heading']}{flag}")
    if fallbacks:
        print(
            f"  WARNING: {len(fallbacks)} heading(s) had no valid [Tag] and were "
            f"routed to DEFAULT_OWNER ({DEFAULT_OWNER}):"
        )
        for heading in fallbacks:
            print(f"    - {heading}")

    routed = route_sections(sections)

    # Only call the model for agents that actually own sections. Agents with an
    # empty bucket get a NOT_APPLICABLE placeholder (so the synthesis agent and the
    # saved report still carry all three domains, and the output still validates).
    print("  running domain agents (isolated, in parallel) ...")
    active = [a for a in DOMAIN_AGENTS if routed[a.domain].strip()]
    skipped = [a for a in DOMAIN_AGENTS if not routed[a.domain].strip()]
    for a in skipped:
        print(f"    skipping {a.domain} agent (no sections routed to it)")

    tasks = {a.domain: run_domain_agent(a, routed[a.domain]) for a in active}
    results_by_domain = dict(zip(tasks.keys(), await asyncio.gather(*tasks.values())))
    for a in skipped:
        results_by_domain[a.domain] = _not_applicable_result(a.domain)

    results = list(results_by_domain.values())
    conflicts = detect_conflicts(results)
    print(f"  detected {len(conflicts)} cross-domain conflict(s)")

    print("  running synthesis agent ...")
    synthesis = await run_synthesis_agent(results, conflicts)

    return {
        "domain_results": results_by_domain,
        "conflicts": conflicts,
        "synthesis": synthesis,
    }


# ---------------------------------------------------------------------------
# Filename-based result caching with content hashing
# ---------------------------------------------------------------------------
async def run_or_get_cached(
    doc_path: Path, force: bool = False, check_content: bool = True
) -> dict:
    """Return the report for one document, using results/<stem>.json as a cache.

    - If the cache file exists and not `force`: load it; if `check_content` is False
      OR the stored content_hash matches the current file's hash, return the cached
      report and skip all model calls. If the content changed, re-test and overwrite.
    - Otherwise run the full pipeline and save the report with `source_file` and
      `content_hash`.
    """
    text = read_markdown_file(doc_path)
    digest = content_hash(text)
    cache_file = RESULTS_DIR / f"{doc_path.stem}.json"

    if cache_file.exists() and not force:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if not check_content or cached.get("content_hash") == digest:
            print(f"  CACHE HIT: {doc_path.name} (hash {digest}) — skipping model calls")
            return cached
        print(
            f"  content changed for {doc_path.name} "
            f"(was {cached.get('content_hash')}, now {digest}) — re-testing"
        )
    else:
        reason = "forced" if force else "no cache"
        print(f"  testing {doc_path.name} (hash {digest}) — {reason}")

    report = await analyze_document(text)
    report["source_file"] = doc_path.name
    report["content_hash"] = digest
    save_json(cache_file, report)
    return report


# ---------------------------------------------------------------------------
# Batch entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the document-governance pipeline over documents/*.md "
        "with filename-based result caching (one results/<doc>.json per document)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the cache and re-test every document.",
    )
    args = parser.parse_args()

    docs = sorted(DOCUMENTS_DIR.glob("*.md"))
    if not docs:
        sys.exit(f"No documents found in {DOCUMENTS_DIR}")

    print(f"Found {len(docs)} document(s) in {DOCUMENTS_DIR.relative_to(ROOT)}.")
    for doc in docs:
        print(f"\n=== {doc.name} ===")
        await run_or_get_cached(doc, force=args.force)

    print(f"\nDone. Reports in {RESULTS_DIR.relative_to(ROOT)}/<doc>.json")


def run() -> None:
    """Synchronous entry point for the console script (see pyproject.toml)."""
    asyncio.run(main())


if __name__ == "__main__":
    run()

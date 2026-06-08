"""SAD governance evaluation — Claude native sub-agents as the execution model.

Pipeline:
    source.md
      -> SHA256 (source_hash)
      -> cache check (key = source_hash + guideline_version)
      -> deterministic section parser  (parser.py decides section ownership)
      -> Claude native orchestrator query()  (delegates via the Agent tool)
           -> domain sub-agents (Data Movement / Security / Resilience)
           -> synthesis sub-agent
      -> results/<doc>.json

The deterministic parts (hashing, caching, parsing, section ownership) stay in Python.
Agent routing/orchestration is done by the Claude native orchestrator, not Python.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python main_orchestrator.py                 # evaluate every documents/*.md
    python main_orchestrator.py documents/x.md  # evaluate one SAD
    python main_orchestrator.py --force ...      # ignore the cache
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

import parser
from agents import EVALUATORS, build_agents, build_orchestrator_prompt
from schema import ACTIVE_GUIDELINE_VERSION
from tools import MCP_SERVER, SERVER_NAME, TOOL_NAMES

ROOT = Path(__file__).parent
DOCUMENTS_DIR = ROOT / "documents"
RESULTS_DIR = ROOT / "results"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_lookup(out_path: Path, source_hash: str, version: str) -> dict | None:
    """Cache hit only when BOTH the source_hash and guideline_version match, so a
    guideline version bump invalidates stale results."""
    if not out_path.exists():
        return None
    try:
        data = json.loads(out_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("source_hash") == source_hash and data.get("guideline_version") == version:
        return data
    return None


async def evaluate_sad(doc_path: Path, force: bool = False) -> dict | str:
    text = doc_path.read_text(encoding="utf-8")
    source_hash = sha256_text(text)
    version = ACTIVE_GUIDELINE_VERSION
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{doc_path.stem}.json"

    # 1) cache
    if not force:
        cached = cache_lookup(out_path, source_hash, version)
        if cached is not None:
            print(f"  CACHE HIT: {doc_path.name} (source_hash {source_hash[:12]}, {version}) — skipping evaluation")
            return cached

    # 2) deterministic parse + section ownership
    sections = parser.parse_sections(text)
    by_domain = parser.sections_by_domain(sections)
    assignments = {
        dom: [f"{s.heading} (lines {s.line_range})" for s in secs]
        for dom, secs in by_domain.items()
    }
    print(f"  source_hash: {source_hash[:12]}  guideline_version: {version}")
    print("  deterministic section ownership:")
    for ev in EVALUATORS:
        owned = assignments.get(ev.key) or ["(none)"]
        print(f"    {ev.key:13s} <- {', '.join(owned)}")

    # 3) Claude native orchestrator (it delegates to the sub-agents)
    options = ClaudeAgentOptions(
        system_prompt=build_orchestrator_prompt(
            doc_path.relative_to(ROOT).as_posix(),
            out_path.relative_to(ROOT).as_posix(),
            source_hash,
            version,
            assignments,
        ),
        cwd=str(ROOT),
        allowed_tools=["Read", "Write", "Glob", "Agent", "Skill", *TOOL_NAMES],
        mcp_servers={SERVER_NAME: MCP_SERVER},
        agents=build_agents(),
        setting_sources=["project"],     # discover .claude/skills (behavior skill)
        permission_mode="acceptEdits",   # auto-accept the result file write
    )
    final = ""
    async for message in query(prompt=f"Run the SAD governance review for {doc_path.name} now.", options=options):
        if getattr(message, "result", None):
            final = message.result

    # 4) stamp the written result so the cache key + provenance are always reliable
    #    (normalize top-level AND every nested evidence item's source_hash/version)
    if out_path.exists():
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            data["source_file"] = doc_path.name
            data["source_hash"] = source_hash
            data["guideline_version"] = version
            for ev_list in [data.get("evidence", [])] + [
                e.get("evidence", []) for e in data.get("evaluations", [])
            ]:
                for item in ev_list or []:
                    if isinstance(item, dict):
                        item["source_hash"] = source_hash
                        item.setdefault("guideline_version", version)
            out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass
    return final


async def main() -> None:
    ap = argparse.ArgumentParser(
        description="SAD governance evaluation via Claude native sub-agents "
        "(Data Movement / Security / Resilience), with SHA256 + version-aware caching."
    )
    ap.add_argument("document", nargs="?", help="One SAD Markdown file. Omit for all documents/*.md.")
    ap.add_argument("--force", action="store_true", help="Ignore the cache and re-evaluate.")
    args = ap.parse_args()

    docs = [Path(args.document).resolve()] if args.document else sorted(
        p.resolve() for p in DOCUMENTS_DIR.glob("*.md")
    )
    if not docs or not all(d.exists() for d in docs):
        sys.exit(f"No SAD document(s) found (looked in {DOCUMENTS_DIR} or the given path).")

    for doc in docs:
        print(f"\n=== Evaluating SAD: {doc.name} ===")
        result = await evaluate_sad(doc, force=args.force)
        if isinstance(result, str) and result:
            print(result)
        print(f"Final assessment at results/{doc.stem}.json")


def run() -> None:
    """Synchronous entry point for the console script (see pyproject.toml)."""
    asyncio.run(main())


if __name__ == "__main__":
    run()

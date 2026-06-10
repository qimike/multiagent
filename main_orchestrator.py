"""SAD governance evaluation — Claude native sub-agents as the execution model.

Pipeline:
    source.md
      -> SHA256 (source_hash)
      -> cache check (key = source_hash + guideline_version)
      -> Claude native orchestrator query()  (delegates via the Agent tool)
           -> Governance Context Agent  (reads the SAD, extracts per-domain context)
           -> domain sub-agents (Data Movement / Security / Resilience)
           -> synthesis sub-agent
      -> results/<doc>.json

Only the deterministic parts (hashing, caching, file read/write) stay in Python. Section
understanding, content extraction, relevance, evaluation, and all agent routing are done by
Claude native agents, NOT by Python.

Run (the SAD document path is REQUIRED — exactly one document per execution):
    export ANTHROPIC_API_KEY=sk-ant-...
    python main_orchestrator.py documents/sample.md
    or
    governance-review documents/sample.md
    Optional:
    governance-review documents/sample.md --force   # ignore the cache
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query
from pydantic import ValidationError

from agents import build_agents, build_orchestrator_prompt
from schema import ACTIVE_GUIDELINE_VERSION, validate_final_output
from tools import MCP_SERVER, SERVER_NAME, TOOL_NAMES

ROOT = Path(__file__).parent
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

    print(f"  source_hash: {source_hash[:12]}  guideline_version: {version}")
    print("  context extraction + evaluation: decided by Claude native agents")

    # 2) Claude native orchestrator (it delegates to the sub-agents, starting with the
    #    Governance Context Agent that extracts per-domain context)
    options = ClaudeAgentOptions(
        system_prompt=build_orchestrator_prompt(
            doc_path.relative_to(ROOT).as_posix(),
            out_path.relative_to(ROOT).as_posix(),
            source_hash,
            version,
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

    # 3) stamp identity, backfill evidence provenance (so it is never lost), then validate
    if out_path.exists():
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = None
        if isinstance(data, dict):
            data["source_file"] = doc_path.name
            data["source_hash"] = source_hash
            data["guideline_version"] = version

            # Backfill provenance on per-evaluation evidence, and remember quote->domain
            # so the consolidated top-level evidence can be backfilled too.
            quote_domain: dict[str, str] = {}
            for ev in data.get("evaluations", []) or []:
                dom = ev.get("guideline_domain")
                for item in ev.get("evidence", []) or []:
                    if isinstance(item, dict):
                        item["source_hash"] = source_hash
                        item.setdefault("guideline_version", version)
                        if dom:
                            item.setdefault("guideline_domain", dom)
                            if item.get("quote"):
                                quote_domain.setdefault(item["quote"], dom)
            for item in data.get("evidence", []) or []:
                if isinstance(item, dict):
                    item["source_hash"] = source_hash
                    item.setdefault("guideline_version", version)
                    if "guideline_domain" not in item and item.get("quote") in quote_domain:
                        item["guideline_domain"] = quote_domain[item["quote"]]

            out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

            # Runtime validation — catch missing fields / malformed output loudly.
            try:
                validate_final_output(data)
                print("  ✓ output validated against schema")
            except ValidationError as exc:
                print(f"  ✗ output FAILED schema validation:\n{exc}", file=sys.stderr)
                sys.exit(1)
    return final


async def main() -> None:
    ap = argparse.ArgumentParser(
        description="SAD governance evaluation via Claude native sub-agents "
        "(Data Movement / Security / Resilience), with SHA256 + version-aware caching."
    )
    ap.add_argument("document", help="Path to the SAD markdown document to evaluate.")
    ap.add_argument("--force", action="store_true", help="Ignore the cache and re-evaluate.")
    args = ap.parse_args()

    # Exactly one SAD per execution; the path is required and must exist. The framework
    # never automatically scans the documents/ directory.
    docs = [Path(args.document).resolve()]
    if not docs[0].exists():
        sys.exit(f"SAD document not found: {docs[0]}")

    doc = docs[0]
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

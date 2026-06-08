"""SAD governance-evaluation pipeline — model-driven orchestration.

A SINGLE parent query() is given the three domain evaluators and a synthesis agent as
AgentDefinitions, plus the Agent tool. The MODEL owns the workflow: it parses the SAD
into sections, routes them, delegates to each evaluator (passing the full SAD + the
relevant section(s)), collects the results, asks the synthesis agent to merge them, and
writes the final assessment. There is no deterministic Python control flow driving the
evaluation — the orchestrator only launches the query and persists nothing itself.

    SAD Markdown
        |
        v
    [Parent orchestrator query() + Agent tool]
        |  parse sections -> route -> dispatch (Agent tool)
        +--> Data Movement Evaluator  --\\
        +--> Security Evaluator        ---> get_guideline + find_evidence (the only tools)
        +--> Resilience Evaluator      --/
        |
        v
    [Synthesis subagent]  merge + dedupe + evidence linkage
        |
        v
    results/<doc>.json  ->  { "overall_status": ..., "evaluations": [...], "evidence": [...] }

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python main_orchestrator.py                 # evaluate every documents/*.md
    python main_orchestrator.py documents/x.md  # evaluate one SAD
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from agents import build_agents, build_orchestrator_prompt
from tools import MCP_SERVER, SERVER_NAME, TOOL_NAMES

ROOT = Path(__file__).parent
DOCUMENTS_DIR = ROOT / "documents"
RESULTS_DIR = ROOT / "results"


async def evaluate_sad(doc_path: Path) -> str:
    """Launch the model-driven review for one SAD. The agent writes the final
    assessment to results/<stem>.json; we return the orchestrator's final text."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{doc_path.stem}.json"

    options = ClaudeAgentOptions(
        system_prompt=build_orchestrator_prompt(
            doc_path.relative_to(ROOT).as_posix(),
            out_path.relative_to(ROOT).as_posix(),
        ),
        cwd=str(ROOT),
        # "Agent" lets the orchestrator spawn the evaluator/synthesis subagents;
        # Read/Write/Glob let it read the SAD and write the result. The mcp__governance__*
        # tools are the evaluators' two tools (pre-approved here, used by the subagents).
        allowed_tools=["Read", "Write", "Glob", "Agent", *TOOL_NAMES],
        mcp_servers={SERVER_NAME: MCP_SERVER},
        agents=build_agents(),
        setting_sources=[],          # no project settings / skills
        permission_mode="acceptEdits",  # auto-accept the result file write
    )

    final = ""
    async for message in query(prompt=f"Run the SAD governance review for {doc_path.name} now.", options=options):
        if getattr(message, "result", None):
            final = message.result
    return final


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Model-driven SAD governance evaluation (Data Movement / Security / "
        "Resilience). Writes results/<doc>.json with {overall_status, evaluations, evidence}."
    )
    parser.add_argument(
        "document",
        nargs="?",
        help="Path to one SAD Markdown file. Omit to evaluate every documents/*.md.",
    )
    args = parser.parse_args()

    if args.document:
        docs = [Path(args.document).resolve()]
    else:
        docs = sorted(p.resolve() for p in DOCUMENTS_DIR.glob("*.md"))
    if not docs or not all(d.exists() for d in docs):
        sys.exit(f"No SAD document(s) found (looked in {DOCUMENTS_DIR} or the given path).")

    for doc in docs:
        print(f"\n=== Evaluating SAD: {doc.name} ===")
        result = await evaluate_sad(doc)
        if result:
            print(result)
        print(f"Final assessment written to results/{doc.stem}.json")


def run() -> None:
    """Synchronous entry point for the console script (see pyproject.toml)."""
    asyncio.run(main())


if __name__ == "__main__":
    run()

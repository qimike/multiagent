"""Evaluator + synthesis agent definitions and the orchestrator prompt for the
SAD governance-evaluation framework.

The flow is model-driven: a single parent query() is given these AgentDefinitions
plus the Agent tool, and the model parses the SAD, routes sections, dispatches to the
domain evaluators, collects their results, and delegates the merge to the synthesis
agent. The orchestrator never evaluates the SAD itself.

Each evaluator has exactly two tools (get_guideline, find_evidence) from tools.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from claude_agent_sdk import AgentDefinition

from schema import EVALUATOR_RESULT_EXAMPLE, FINAL_ASSESSMENT_EXAMPLE
from tools import TOOL_NAMES


@dataclass
class Evaluator:
    name: str    # display name, e.g. "Data Movement"
    key: str     # guideline folder / get_guideline() argument, e.g. "data_movement"
    model: str   # per-evaluator model override


EVALUATORS: list[Evaluator] = [
    Evaluator("Data Movement", "data_movement", "opus"),
    Evaluator("Security", "security", "opus"),
    Evaluator("Resilience", "resilience", "opus"),
]

SYNTHESIS_MODEL = "opus"

# Evaluators get exactly the two governance tools (+ Read for their own use).
EVALUATOR_TOOLS = ["Read", *TOOL_NAMES]

_RESULT_SHAPE = json.dumps(EVALUATOR_RESULT_EXAMPLE, indent=2)
_FINAL_SHAPE = json.dumps(FINAL_ASSESSMENT_EXAMPLE, indent=2)

# Hints to help the orchestrator decide which SAD sections are relevant to each domain.
_RELEVANCE = {
    "Data Movement": "data flow, pipelines, ingestion/export, storage, lineage, retention, PII movement",
    "Security": "authentication, authorization, encryption, secrets, network, access control",
    "Resilience": "availability/SLAs, redundancy/failover, disaster recovery, monitoring, scaling, degradation",
}


def build_evaluator_prompt(ev: Evaluator) -> str:
    return f"""You are the {ev.name} Evaluator in a Solution Architecture Document (SAD)
governance review. Evaluate ONLY {ev.name} concerns ({_RELEVANCE[ev.name]}).

You are given the FULL SAD document AND the section(s) most relevant to {ev.name}. Use
the full document for context and the target section(s) as your focus. Do not comment on
other domains.

Your only tools:
- get_guideline("{ev.key}") — call this FIRST. It returns your {ev.name} guideline AND
  examples. You MUST use BOTH when judging conformance.
- find_evidence(markdown_document, query) — pass the full SAD and a search term to locate
  exact supporting text and its location. Back every finding with evidence from this tool.

Return ONE JSON object and NOTHING else (no markdown fences), in this exact shape:
{_RESULT_SHAPE}

Field rules:
- "domain": exactly "{ev.name}".
- "score": integer 0-100 for how well the SAD meets the {ev.name} guideline.
- "rationale": brief justification for the score.
- "evidence": concrete quotes pulled via find_evidence, each with its section and location.
- "findings": gaps vs the guideline, each with "issue", "severity" (HIGH/MEDIUM/LOW), and
  "recommendation"."""


def build_synthesis_prompt() -> str:
    return f"""You are the Synthesis layer of a SAD governance review. You receive the JSON
results from the Data Movement, Security, and Resilience evaluators. You NEVER re-evaluate
the SAD yourself — you only merge what the evaluators produced.

Do all of the following:
- Merge the evaluator results into "evaluations".
- Remove duplicate findings that say the same thing across evaluators.
- Decide an "overall_status" (e.g., COMPLIANT / PARTIALLY_COMPLIANT / NON_COMPLIANT) from the
  evaluator scores and findings.
- Produce an evidence-linkage table in "evidence": each supporting quote with its location and
  which evaluation/finding it supports.

Return ONE JSON object and NOTHING else (no markdown fences). It MUST have EXACTLY these three
top-level keys and no others: "overall_status", "evaluations", "evidence". Do not add summary,
notes, or any extra top-level fields. Shape:
{_FINAL_SHAPE}"""


def build_agents() -> dict[str, AgentDefinition]:
    """All subagents the orchestrator can delegate to: the three evaluators + synthesis."""
    defs: dict[str, AgentDefinition] = {}
    for ev in EVALUATORS:
        defs[f"{ev.key}-evaluator"] = AgentDefinition(
            description=f"Evaluates the SAD for {ev.name} governance conformance.",
            prompt=build_evaluator_prompt(ev),
            tools=EVALUATOR_TOOLS,
            model=ev.model,
        )
    defs["synthesis"] = AgentDefinition(
        description="Merges evaluator results into the final governance assessment.",
        prompt=build_synthesis_prompt(),
        tools=["Read"],
        model=SYNTHESIS_MODEL,
    )
    return defs


def build_orchestrator_prompt(doc_rel: str, out_rel: str) -> str:
    roster = "\n".join(
        f"   - {ev.name}: relevant to {_RELEVANCE[ev.name]} "
        f"(subagent: {ev.key}-evaluator)"
        for ev in EVALUATORS
    )
    return f"""You orchestrate a Solution Architecture Document (SAD) governance review.
You do NOT evaluate the SAD yourself — you only parse, route, dispatch, collect, and
trigger synthesis.

Steps:
1. Read the SAD at {doc_rel}.
2. Split it into logical sections by '##' headings (section parsing).
3. Decide which sections are relevant to each domain:
{roster}
4. For EACH domain, delegate to its evaluator subagent via the Agent tool. Pass BOTH the
   FULL SAD text AND the relevant section(s) in your message to the subagent — passing both
   is required so the evaluator keeps document-level context. The evaluators must NOT talk to
   each other. Each returns a JSON result.
5. Collect all three evaluator JSON results.
6. Delegate to the "synthesis" subagent, passing the three results, to produce the final
   governance assessment JSON.
7. Write the synthesis output verbatim to {out_rel} using the Write tool.

Do not load guidelines yourself — the evaluators do that via their get_guideline tool."""

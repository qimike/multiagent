"""Claude native sub-agent definitions + the orchestrator prompt.

Claude SDK AgentDefinitions are the primary execution model: a single parent query()
is given these sub-agents plus the Agent tool. The orchestrator delegates evaluation to
the domain sub-agents and the synthesis agent — it performs no evaluation itself.

Section ownership is decided deterministically by parser.py and passed into the
orchestrator prompt; the sub-agents only evaluate the sections assigned to them.

Governance content is NOT in skills — the shared `governance-evaluation` skill holds
evaluation behavior/format only, and the sub-agents load the versioned guideline at
runtime via the get_guideline tool.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from claude_agent_sdk import AgentDefinition

from schema import EVALUATOR_RESULT_EXAMPLE, FINAL_OUTPUT_EXAMPLE
from tools import TOOL_NAMES

SHARED_SKILL = "governance-evaluation"
SYNTHESIS_MODEL = "opus"

# Sub-agents get the shared MCP tools, Read, and the Skill tool (to load the behavior skill).
EVALUATOR_TOOLS = ["Read", "Skill", *TOOL_NAMES]

_RESULT_SHAPE = json.dumps(EVALUATOR_RESULT_EXAMPLE, indent=2)
_FINAL_SHAPE = json.dumps(FINAL_OUTPUT_EXAMPLE, indent=2)


@dataclass
class Evaluator:
    name: str    # display name, e.g. "Data Movement"
    key: str     # domain key / get_guideline argument, e.g. "data_movement"
    model: str


EVALUATORS: list[Evaluator] = [
    Evaluator("Data Movement", "data_movement", "opus"),
    Evaluator("Security", "security", "opus"),
    Evaluator("Resilience", "resilience", "opus"),
]


def build_evaluator_prompt(ev: Evaluator) -> str:
    return f"""You are the {ev.name} Evaluator (domain key: "{ev.key}").

Load and follow the "{SHARED_SKILL}" skill — it defines your procedure, reasoning, and
the exact JSON output format. Evaluate ONLY the "{ev.key}" domain.

You will be given: the active guideline version, the source_hash, the full SAD, and the
specific section(s) assigned to you (ownership was decided deterministically — do not
reassign or discover sections). Steps:
1. Call get_guideline("{ev.key}", <version>) and use BOTH the guideline and examples.
2. Evaluate your assigned section text against the guideline. Generate evidence DIRECTLY
   from the section text you already have — find_evidence is an OPTIONAL helper, not
   required.
3. Keep finding, reasoning, and evidence distinct:
   - finding = your conclusion for this domain;
   - reasoning = why the evidence satisfies or violates the guideline;
   - evidence = EXACT, verbatim quotations from the SAD (never paraphrase, never
     fabricate; if a control is absent, say so in the finding rather than inventing a quote).
4. Every evidence item MUST carry full provenance: section, line_range, guideline_domain
   ("{ev.key}"), guideline_version, and source_hash (the source_hash you were given).
5. Return ONE JSON object in this exact shape:
{_RESULT_SHAPE}"""


def build_synthesis_prompt() -> str:
    return f"""You are the Synthesis Agent. You receive the per-domain evaluator JSON
results (Data Movement, Security, Resilience), plus the source_file, source_hash, and
guideline_version. You do NOT re-evaluate the SAD.

Do all of the following:
- Collect the evaluator outputs verbatim into "evaluations" (keep each domain's finding,
  reasoning, status, severity, evidence, and confidence).
- Merge the findings/reasoning across domains and consolidate all evidence into the
  top-level "evidence" array. Each evidence item is an exact quote that MUST keep its full
  provenance: {{"quote", "section", "line_range", "guideline_domain", "guideline_version",
  "source_hash"}}. Do NOT paraphrase quotes and do NOT drop any provenance field.
- Compute an overall "evaluation_result" (CONFORM | PARTIAL | NON_CONFORM) and overall
  "confidence" from the per-domain results.

Return ONE JSON object and NOTHING else (no markdown fences), with EXACTLY these top-level
keys: source_file, source_hash, guideline_version, evaluation_result, confidence,
evaluations, evidence. Shape:
{_FINAL_SHAPE}"""


def build_agents() -> dict[str, AgentDefinition]:
    """The sub-agents the orchestrator can delegate to: 3 evaluators + synthesis."""
    defs: dict[str, AgentDefinition] = {}
    for ev in EVALUATORS:
        defs[f"{ev.key}-evaluator"] = AgentDefinition(
            description=f"Evaluates the SAD's assigned {ev.name} sections for conformance.",
            prompt=build_evaluator_prompt(ev),
            tools=EVALUATOR_TOOLS,
            skills=[SHARED_SKILL],
            model=ev.model,
        )
    defs["synthesis"] = AgentDefinition(
        description="Merges evaluator results into the final governance assessment.",
        prompt=build_synthesis_prompt(),
        tools=["Read"],
        model=SYNTHESIS_MODEL,
    )
    return defs


def build_orchestrator_prompt(
    doc_rel: str,
    out_rel: str,
    source_hash: str,
    version: str,
    assignments: dict[str, list[str]],
) -> str:
    """assignments: {domain_key: ["Heading (lines a-b)", ...]} from the deterministic parser."""
    lines = []
    for ev in EVALUATORS:
        owned = assignments.get(ev.key) or []
        owned_txt = "; ".join(owned) if owned else "(no sections assigned — skip this evaluator)"
        lines.append(f"   - {ev.name} ({ev.key}-evaluator): {owned_txt}")
    roster = "\n".join(lines)

    return f"""You orchestrate a Solution Architecture Document (SAD) governance review using
native sub-agents. You do NOT evaluate the SAD yourself, and you do NOT decide section
ownership — ownership was already computed deterministically and is given below.

Context:
- SAD file: {doc_rel}
- source_hash: {source_hash}
- guideline_version: {version}

Deterministic section ownership (each section belongs to exactly one domain):
{roster}

Steps:
1. Read the SAD at {doc_rel} (for the section text to pass along).
2. For EACH domain that has assigned sections, delegate to its evaluator sub-agent via the
   Agent tool. In your message to the sub-agent include: its guideline_version ({version}),
   the source_hash ({source_hash}), the FULL SAD text, and the text of ITS assigned
   section(s) only. Sub-agents must NOT talk to each other. Skip any evaluator with no
   assigned sections.
3. Collect the evaluator JSON results.
4. Delegate to the "synthesis" sub-agent, passing the evaluator results plus source_file
   ("{doc_rel.split('/')[-1]}"), source_hash ({source_hash}), and guideline_version
   ({version}), to produce the final assessment.
5. Write the synthesis output verbatim to {out_rel} using the Write tool.

Do not load guidelines yourself — the evaluators do that via get_guideline."""

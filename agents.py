"""Claude native sub-agent definitions + the orchestrator prompt.

Claude SDK AgentDefinitions are the primary execution model: a single parent query()
is given these sub-agents plus the Agent tool. The orchestrator delegates ALL reasoning
to sub-agents — it performs no evaluation and no section routing itself.

Section ownership is decided SEMANTICALLY by the `section-assignment` agent (Claude),
NOT by Python. Python no longer contains any heading regex or routing map. The
orchestrator invokes section-assignment first, then hands each domain evaluator the
sections that agent assigned to it.

Governance content is NOT in skills — the shared `governance-evaluation` skill holds
evaluation behavior/format only, and the sub-agents load the versioned guideline at
runtime via the get_guideline tool.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from claude_agent_sdk import AgentDefinition

from domains import DOMAIN_CONFIG
from schema import (
    EVALUATOR_RESULT_EXAMPLE,
    FINAL_OUTPUT_EXAMPLE,
    SECTION_ASSIGNMENT_EXAMPLE,
)
from tools import TOOL_NAMES

SHARED_SKILL = "governance-evaluation"
SYNTHESIS_MODEL = "opus"
SECTION_ASSIGNMENT_MODEL = "opus"
SECTION_ASSIGNMENT_AGENT = "section-assignment"

# Sub-agents get the shared MCP tools, Read, and the Skill tool (to load the behavior skill).
EVALUATOR_TOOLS = ["Read", "Skill", *TOOL_NAMES]

_RESULT_SHAPE = json.dumps(EVALUATOR_RESULT_EXAMPLE, indent=2)
_FINAL_SHAPE = json.dumps(FINAL_OUTPUT_EXAMPLE, indent=2)
_ASSIGNMENT_SHAPE = json.dumps(SECTION_ASSIGNMENT_EXAMPLE, indent=2)


@dataclass
class Evaluator:
    name: str    # display name, e.g. "Data Movement"
    key: str     # domain key / get_guideline argument, e.g. "data_movement"
    model: str
    scope: str   # short description of the domain's concerns


# Derived from the single source of truth in domains.py.
EVALUATORS: list[Evaluator] = [
    Evaluator(cfg["name"], key, cfg["model"], cfg["scope"])
    for key, cfg in DOMAIN_CONFIG.items()
]


def build_section_assignment_prompt() -> str:
    domains_block = "\n".join(
        f'   - "{ev.key}" ({ev.name}): {ev.scope}' for ev in EVALUATORS
    )
    keys = ", ".join(f'"{ev.key}"' for ev in EVALUATORS)
    return f"""You are the Section Assignment Agent. You read an ENTIRE Solution
Architecture Document (SAD) and decide, semantically, which governance domain(s) should
evaluate each section. You are the ONLY component that decides section ownership — do not
defer to heading names or numbering conventions; reason about what each section actually
describes.

The governance domains and what each one cares about:
{domains_block}

Method:
1. Read the full SAD you are given.
2. For each section, understand its PURPOSE (not just its title).
3. Assign the section to every domain whose concerns it materially addresses.
   - A section MAY belong to multiple domains (e.g. a cross-functional requirements
     section that covers both security and resilience).
   - A section MAY belong to no domain if it is purely contextual (executive summary,
     business goals, document metadata, ADR index, etc.) — simply omit it.
4. Identify each section by its section number when one is present (e.g. "4.2", "9"); if a
   section has no number, use its heading text. Use the identifier exactly as it appears in
   the SAD so the downstream evaluators can locate it.

Base every decision on the section's content and the domain scopes above — NOT on keyword
matching. The same word can appear in a section that belongs to a different domain.

Return ONE JSON object and NOTHING else (no markdown fences), with EXACTLY these keys
({keys}); each value is the list of section identifiers assigned to that domain (use an
empty list if a domain owns no sections):
{_ASSIGNMENT_SHAPE}"""


def build_evaluator_prompt(ev: Evaluator) -> str:
    return f"""You are the {ev.name} Evaluator (domain key: "{ev.key}").

Load and follow the "{SHARED_SKILL}" skill — it defines your procedure, reasoning, and
the exact JSON output format. Evaluate ONLY the "{ev.key}" domain, which covers:
{ev.scope}.

You will be given: the active guideline version, the source_hash, the full SAD, and the
specific section(s) assigned to you. The section-assignment agent already decided this
ownership semantically — do NOT reassign, discover, or second-guess which sections are
yours. Steps:
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
   ("{ev.key}"), guideline_version, source_hash (the source_hash you were given), and an
   evidence_confidence (0.0-1.0) for how strongly that quote supports the finding.
5. Return ONE JSON object in this exact shape:
{_RESULT_SHAPE}"""


def build_synthesis_prompt() -> str:
    return f"""You are the Synthesis Agent — an AGGREGATOR, not a second evaluator. You
receive the per-domain evaluator JSON results (Data Movement, Security, Resilience), plus
the source_file, source_hash, and guideline_version. You do NOT re-evaluate the SAD.

Preserve evaluator outputs verbatim:
- Do NOT rewrite evaluator findings.
- Do NOT reinterpret evaluator reasoning.
- Do NOT change evaluator severity.
- Do NOT change evaluator status.
- Only aggregate and consolidate duplicated findings/evidence.
(e.g. if the Security evaluator returned status=NON_CONFORM, severity=HIGH, you must NOT
downgrade it.)

Do all of the following:
- Collect the evaluator outputs verbatim into "evaluations" (keep each domain's finding,
  reasoning, status, severity, evidence, and confidence exactly as returned).
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
    """The sub-agents the orchestrator can delegate to: section-assignment + 3 evaluators
    + synthesis."""
    defs: dict[str, AgentDefinition] = {}
    defs[SECTION_ASSIGNMENT_AGENT] = AgentDefinition(
        description="Reads the full SAD and semantically assigns each section to the "
        "governance domain(s) that should evaluate it.",
        prompt=build_section_assignment_prompt(),
        tools=["Read"],
        model=SECTION_ASSIGNMENT_MODEL,
    )
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
) -> str:
    roster = "\n".join(
        f'   - {ev.name}: "{ev.key}-evaluator" (domain key "{ev.key}")'
        for ev in EVALUATORS
    )
    domain_keys = ", ".join(f'"{ev.key}"' for ev in EVALUATORS)

    return f"""You orchestrate a Solution Architecture Document (SAD) governance review using
native sub-agents. You do NOT evaluate the SAD yourself, and you do NOT decide section
ownership — a dedicated section-assignment agent decides ownership semantically.

Context:
- SAD file: {doc_rel}
- source_hash: {source_hash}
- guideline_version: {version}

Available domain evaluators:
{roster}

Steps:
1. Read the SAD at {doc_rel} (you will pass its full text to the sub-agents).
2. Delegate to the "{SECTION_ASSIGNMENT_AGENT}" sub-agent via the Agent tool, passing it the
   FULL SAD text. It returns a JSON object mapping each domain key ({domain_keys}) to the
   list of section identifiers that domain should evaluate. Treat this assignment as
   authoritative — do NOT override it.
3. For EACH domain that was assigned one or more sections, delegate to its evaluator
   sub-agent via the Agent tool. In your message to the evaluator include: its
   guideline_version ({version}), the source_hash ({source_hash}), the FULL SAD text, and
   the list of section identifiers assigned to it by the section-assignment agent. Skip any
   domain whose assigned list is empty. Sub-agents must NOT talk to each other.
4. Collect the evaluator JSON results.
5. Delegate to the "synthesis" sub-agent, passing the evaluator results plus source_file
   ("{doc_rel.split('/')[-1]}"), source_hash ({source_hash}), and guideline_version
   ({version}), to produce the final assessment.
6. Write the synthesis output verbatim to {out_rel} using the Write tool.

Do not load guidelines yourself — the evaluators do that via get_guideline. Do not assign
sections yourself — the section-assignment agent does that."""

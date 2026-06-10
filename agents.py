"""Claude native sub-agent definitions + the orchestrator prompt.

Claude SDK AgentDefinitions are the primary execution model: a single parent query()
is given these sub-agents plus the Agent tool. The orchestrator delegates ALL reasoning
to sub-agents — it performs no evaluation, no content extraction, and no routing itself.

Flow (all model-driven; Python only hashes, caches, reads, and writes):
  Governance Context Agent  -> reads the full SAD, understands every section, and EXTRACTS
                               the content relevant to each domain (security / resilience /
                               data_movement) as {section_header, content} objects.
  Orchestrator              -> for each non-empty domain context, delegates to that domain's
                               evaluator, collects results, then delegates to synthesis.
  Domain evaluators         -> evaluate the supplied domain context against the guideline.
  Synthesis                 -> merges evaluator outputs into the final assessment.

Governance content is NOT in skills — the shared `governance-evaluation` skill holds
evaluation behavior/format only, and the sub-agents load the versioned guideline at
runtime via the get_guideline tool (the only governance MCP tool).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from claude_agent_sdk import AgentDefinition

from domains import DOMAIN_CONFIG
from schema import (
    EVALUATOR_RESULT_EXAMPLE,
    FINAL_OUTPUT_EXAMPLE,
    GOVERNANCE_CONTEXT_EXAMPLE,
)
from tools import TOOL_NAMES

SHARED_SKILL = "governance-evaluation"
SYNTHESIS_MODEL = "opus"
GOVERNANCE_CONTEXT_MODEL = "opus"
GOVERNANCE_CONTEXT_AGENT = "governance-context"

# Evaluators get the shared MCP guideline tool and the Skill tool (to load the behavior
# skill). They do NOT get Read or any search tool — they only evaluate the domain context
# handed to them, generating evidence directly from that content.
EVALUATOR_TOOLS = ["Skill", *TOOL_NAMES]

_RESULT_SHAPE = json.dumps(EVALUATOR_RESULT_EXAMPLE, indent=2)
_FINAL_SHAPE = json.dumps(FINAL_OUTPUT_EXAMPLE, indent=2)
_CONTEXT_SHAPE = json.dumps(GOVERNANCE_CONTEXT_EXAMPLE, indent=2)


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


def context_key(domain_key: str) -> str:
    """The Governance Context output key for a domain (e.g. 'security' -> 'security_context')."""
    return f"{domain_key}_context"


def build_governance_context_prompt() -> str:
    domains_block = "\n".join(
        f'   - "{ev.key}" ({ev.name}): {ev.scope}' for ev in EVALUATORS
    )
    keys = ", ".join(f'"{context_key(ev.key)}"' for ev in EVALUATORS)
    return f"""You are the Governance Context Agent. You are the FIRST AI agent in the
review. You read an ENTIRE Solution Architecture Document (SAD), understand the purpose of
every section, and EXTRACT the content relevant to each governance domain. You perform both
section understanding AND content extraction — no separate extraction stage exists after
you.

You do NOT evaluate the SAD, you do NOT invoke other agents, and you do NOT route work.
You only return structured, extracted context.

The governance domains and what each one cares about:
{domains_block}

Method:
1. Read the full SAD you are given.
2. Understand the PURPOSE of each section (not just its title).
3. For each domain, collect every section whose content materially addresses that domain's
   concerns, and extract that section's relevant content.
   - A section MAY contribute to multiple domains (e.g. a cross-functional requirements
     section can contribute to both security and resilience) — include it under each.
   - A section MAY be ignored if it is purely informational (executive summary, business
     goals, document metadata, ADR index, etc.) — simply omit it.
4. For every extracted item return BOTH:
   - "section_header": the section's heading exactly as it appears in the SAD (include its
     number when present, e.g. "4.4 Security View – Dataverse to Snowflake").
   - "content": the relevant text of that section, extracted verbatim from the SAD so the
     evaluators can quote it directly. Do NOT return only section numbers.

Base every decision on the section's content and the domain scopes above — NOT on keyword
matching.

Return ONE JSON object and NOTHING else (no markdown fences), with EXACTLY these keys
({keys}); each value is a list of {{"section_header", "content"}} objects (use an empty
list if a domain has no relevant content):
{_CONTEXT_SHAPE}"""


def build_evaluator_prompt(ev: Evaluator) -> str:
    return f"""You are the {ev.name} Evaluator (domain key: "{ev.key}").

Load and follow the "{SHARED_SKILL}" skill — it defines your procedure, reasoning, and
the exact JSON output format. Evaluate ONLY the "{ev.key}" domain, which covers:
{ev.scope}.

You will be given exactly three inputs: the guideline_version, the source_hash, and your
domain_context — a list of {{"section_header", "content"}} objects that the Governance
Context Agent already extracted for you. You do NOT discover sections, route content, or
search for evidence; everything you evaluate is in the domain_context you were given. Steps:
1. Call get_guideline("{ev.key}", <version>) and use BOTH the guideline and examples.
2. Compare the guideline requirements against your domain_context. Generate evidence
   DIRECTLY from the supplied content.
3. Keep finding, reasoning, and evidence distinct:
   - finding = your conclusion for this domain;
   - reasoning = why the evidence satisfies or violates the guideline;
   - evidence = EXACT, verbatim quotations from the supplied content (never paraphrase,
     never fabricate; if a control is absent from the context, say so in the finding rather
     than inventing a quote).
4. Every evidence item MUST carry full provenance: section_header (the section_header from
   your domain_context), line_range (if known; otherwise a best effort or "n/a"),
   guideline_domain ("{ev.key}"), guideline_version, source_hash (the source_hash you were
   given), and an evidence_confidence (0.0-1.0) for how strongly that quote supports the
   finding.
5. Return ONE JSON object in this exact shape:
{_RESULT_SHAPE}"""


def build_synthesis_prompt() -> str:
    return f"""You are the Synthesis Agent — an AGGREGATOR, not a second evaluator. The
Orchestrator gives you the per-domain evaluator JSON results (Data Movement, Security,
Resilience), plus the source_file, source_hash, and guideline_version. You do NOT
re-evaluate the SAD, and you receive results only from the Orchestrator (never directly
from the evaluators).

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
  provenance: {{"quote", "section_header", "line_range", "guideline_domain",
  "guideline_version", "source_hash"}}. Do NOT paraphrase quotes and do NOT drop any
  provenance field.
- Compute an overall "evaluation_result" (CONFORM | PARTIAL | NON_CONFORM) and overall
  "confidence" from the per-domain results.

Return ONE JSON object and NOTHING else (no markdown fences), with EXACTLY these top-level
keys: source_file, source_hash, guideline_version, evaluation_result, confidence,
evaluations, evidence. Shape:
{_FINAL_SHAPE}"""


def build_agents() -> dict[str, AgentDefinition]:
    """The sub-agents the orchestrator can delegate to: governance-context + 3 evaluators
    + synthesis."""
    defs: dict[str, AgentDefinition] = {}
    defs[GOVERNANCE_CONTEXT_AGENT] = AgentDefinition(
        description="Reads the full SAD, understands every section, and extracts the "
        "content relevant to each governance domain as {section_header, content} objects.",
        prompt=build_governance_context_prompt(),
        tools=["Read"],
        model=GOVERNANCE_CONTEXT_MODEL,
    )
    for ev in EVALUATORS:
        defs[f"{ev.key}-evaluator"] = AgentDefinition(
            description=f"Evaluates the supplied {ev.name} domain context for conformance.",
            prompt=build_evaluator_prompt(ev),
            tools=EVALUATOR_TOOLS,
            skills=[SHARED_SKILL],
            model=ev.model,
        )
    defs["synthesis"] = AgentDefinition(
        description="Merges evaluator results into the final governance assessment.",
        prompt=build_synthesis_prompt(),
        tools=[],
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
        f'   - {ev.name}: context key "{context_key(ev.key)}" -> "{ev.key}-evaluator"'
        for ev in EVALUATORS
    )

    return f"""You orchestrate a Solution Architecture Document (SAD) governance review using
native sub-agents. You manage the workflow only: you do NOT evaluate the SAD, you do NOT
extract content, and you do NOT decide relevance yourself.

Context:
- SAD file: {doc_rel}
- source_hash: {source_hash}
- guideline_version: {version}

Domain context keys and their evaluators:
{roster}

Steps:
1. Read the SAD at {doc_rel} (you will pass its full text to the Governance Context Agent).
2. Delegate to the "{GOVERNANCE_CONTEXT_AGENT}" sub-agent via the Agent tool, passing it the
   FULL SAD text. It returns a JSON object with per-domain extracted context, where each
   domain key maps to a list of {{"section_header", "content"}} objects.
3. Based on the Governance Context output, delegate evaluation to the relevant evaluator
   agents: for each domain context that contains extracted content, invoke that domain's
   evaluator sub-agent via the Agent tool. In your message to the evaluator include ONLY:
   its guideline_version ({version}), the source_hash ({source_hash}), and that domain's
   extracted context (the list of {{section_header, content}} objects). Do NOT send the full
   SAD — the evaluators work solely from the extracted context. A domain context with no
   content needs no evaluator. Sub-agents must NOT talk to each other.
4. Collect the evaluator JSON results yourself.
5. Delegate to the "synthesis" sub-agent, passing the collected evaluator results plus
   source_file ("{doc_rel.split('/')[-1]}"), source_hash ({source_hash}), and
   guideline_version ({version}), to produce the final assessment.
6. Write the synthesis output verbatim to {out_rel} using the Write tool.

Delegation is your job: reason over the Governance Context output and invoke the evaluator
agents whose domains have extracted content. Do not load guidelines yourself — the
evaluators do that via get_guideline. Do not extract content yourself — the Governance
Context Agent does that."""

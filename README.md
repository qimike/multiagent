# SAD Governance Evaluation — Claude Native Sub-Agents

Evaluates a **Solution Architecture Document (SAD)** in Markdown against versioned
governance guidelines and produces an evidence-backed, auditable assessment. The
execution model is **Claude SDK native sub-agents**; deterministic work (hashing,
caching, parsing, section ownership) stays in Python.

## Pipeline

```text
source.md
  → SHA256 (source_hash)
  → cache check            (key = source_hash + guideline_version)
  → deterministic parser   (parser.py decides section ownership — agents never do)
  → Claude native orchestrator query()  (delegates via the Agent tool)
       → Data Movement / Security / Resilience sub-agents
       → Synthesis sub-agent
  → results/<doc>.json
```

Python is a thin deterministic pre-processor; the **orchestrator agent** does the
routing-to-sub-agents and the sub-agents do the evaluation. The orchestrator never
evaluates the SAD itself.

## Deterministic section ownership

`parser.py` splits the SAD by Markdown headings and assigns **each section to exactly
one domain** (or none, for context), producing a routing map like:

```json
{ "Data Flow": "data_movement", "Security": "security", "Resilience": "resilience" }
```

Sub-agents only evaluate the sections assigned to them — they do **not** discover
sections or decide ownership.

## SHA256 + caching

Every SAD is hashed (`source_hash`) and the hash is stored in the output. Before
evaluating, the cache is checked with key **`source_hash` + `guideline_version`**:
a matching result is returned without calling the model. Bumping a guideline version
invalidates stale results.

## Versioned guidelines (governance content)

```text
guidelines/<domain>/v1/guideline.md
guidelines/<domain>/v1/examples.md
```

New versions (`v2`, `v3`, …) drop in as sibling folders — **no skill changes needed**.
Domains: `data_movement`, `security`, `resilience`.

## Skills (behavior only — no governance content)

The shared `.claude/skills/governance-evaluation/SKILL.md` holds **evaluation behavior,
reasoning strategy, and output format** only. Governance rules are **not** in the skill;
each sub-agent loads them at runtime via `get_guideline(domain, version)`.

## Tools — one shared MCP server (`governance`)

| Tool | Purpose |
|------|---------|
| `get_guideline(domain, version)` | Load the versioned guideline **and** examples |
| `find_evidence(markdown_document, query)` | **Optional** BM25 helper to locate text/line numbers — evaluators are **not required** to call it |

A single in-process MCP server is shared by all agents (no per-domain server).

## Evidence model & provenance

Evidence is generated **directly during evaluation** and every `quote` is an **exact,
verbatim** substring of the SAD (never paraphrased). Each evaluator keeps **finding**
(the conclusion), **reasoning** (why the evidence satisfies/violates the guideline), and
**evidence** (the exact quotes) distinct. `find_evidence` is only an optional helper.

Every evidence item carries full **provenance** for auditability/reproducibility:
`section`, `line_range`, `guideline_domain`, `guideline_version`, `source_hash`, plus an
`evidence_confidence` (how strongly that quote supports the finding). Synthesis preserves
these fields verbatim (it aggregates, it does not re-evaluate), and Python backfills the
provenance after the run so it is never lost.

## Validation

The final written output is validated at runtime with **Pydantic** models
(`schema.py: validate_final_output`). Malformed or incomplete output (missing fields,
bad enum values) fails loudly with a non-zero exit instead of shipping silently.

## Output schema (`results/<doc>.json`)

```json
{
  "source_file": "source.md",
  "source_hash": "…",
  "guideline_version": "v1",
  "evaluation_result": "NON_CONFORM",
  "confidence": 0.9,
  "evaluations": [
    { "guideline_domain": "security", "guideline_version": "v1",
      "status": "PARTIAL", "severity": "HIGH",
      "finding": "…", "reasoning": "…", "confidence": 0.9,
      "evidence": [ { "quote": "…exact SAD text…", "section": "Security", "line_range": "29-30",
                      "guideline_domain": "security", "guideline_version": "v1", "source_hash": "…",
                      "evidence_confidence": 0.98 } ] }
  ],
  "evidence": [ { "quote": "…exact SAD text…", "section": "Security", "line_range": "29-30",
                  "guideline_domain": "security", "guideline_version": "v1", "source_hash": "…" } ]
}
```

## Setup & run

    pip install -e .
    export ANTHROPIC_API_KEY=sk-ant-...

    # The SAD document path is REQUIRED — exactly one document per run.
    governance-review documents/source.md            # evaluate one SAD
    governance-review documents/source.md --force    # ignore the cache
    # or: python main_orchestrator.py documents/source.md [--force]

## Adding / configuring domains

`domains.py` is the **single source of truth** (`DOMAIN_CONFIG`): each domain's display
name, evaluator model, and heading-routing regex live there, and `parser.py`,
`agents.py`, and `schema.py` all derive from it. To add a domain (API, Cost, Cloud, …),
add an entry to `DOMAIN_CONFIG` plus `guidelines/<domain>/<version>/` — no other code
changes.

## Project layout

    documents/*.md                          # SAD(s) under review
    guidelines/<domain>/<version>/          # guideline.md + examples.md (governance content)
    .claude/skills/governance-evaluation/   # behavior-only skill
    domains.py                              # DOMAIN_CONFIG — single source of truth (routing/name/model)
    parser.py                               # deterministic section parser + ownership (routing from domains.py)
    tools.py                                # shared MCP server: get_guideline, find_evidence (optional locator)
    agents.py                               # sub-agent AgentDefinitions + orchestrator prompt
    schema.py                               # output shapes + Pydantic validation
    main_orchestrator.py                    # hashing, caching, parsing, launches the native orchestrator
    results/<doc>.json                      # final assessment (cache + audit record)

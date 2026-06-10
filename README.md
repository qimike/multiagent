# SAD Governance Evaluation — Claude Native Sub-Agents

Evaluates a **Solution Architecture Document (SAD)** in Markdown against versioned
governance guidelines and produces an evidence-backed, auditable assessment. The
execution model is **Claude SDK native sub-agents**; only deterministic work (hashing,
caching, file read/write) stays in Python — **everything else is model-driven**.

## Pipeline

```text
source.md
  → SHA256 (source_hash)
  → cache check            (key = source_hash + guideline_version)
  → Claude native orchestrator query()  (delegates via the Agent tool)
       → Governance Context Agent   (reads the SAD, extracts per-domain context)
       → Data Movement / Security / Resilience sub-agents
       → Synthesis sub-agent
  → results/<doc>.json
```

Python is a thin deterministic pre-processor (hash + cache + file I/O only); the
**orchestrator agent** manages the workflow, the **Governance Context Agent** does section
understanding and content extraction, the domain sub-agents evaluate, and synthesis
aggregates. The orchestrator never evaluates the SAD itself.

## Governance Context Agent (Claude, not Python)

There is **no heading regex, routing map, or deterministic section-routing stage** anywhere
in Python. The `governance-context` Claude native agent is the first AI agent after the
cache check. It reads the entire SAD, understands the purpose of each section, and
**extracts the relevant content** for each domain — returning both the `section_header` and
the `content` so no downstream extraction stage is needed:

```json
{
  "data_movement_context": [
    { "section_header": "4.2 Archival Data Flow", "content": "Extract case records from Dataverse … Load into Snowflake …" }
  ],
  "security_context": [
    { "section_header": "4.4 Security View – Dataverse to Snowflake", "content": "Azure AD OAuth2 … Snowflake RBAC … TLS 1.2+ …" }
  ],
  "resilience_context": [
    { "section_header": "4.3 Resiliency Design", "content": "ADF Automatic Retry … Snowflake Cross Region Replication …" }
  ]
}
```

A section may contribute to **multiple** domains, or to **none** (purely informational
sections like the executive summary are omitted). The Governance Context Agent does NOT
invoke other agents or route work — it only returns extracted context. The **orchestrator**
then invokes a domain evaluator for each non-empty context (prompt-driven routing, no
Python `if/else`). Domain sub-agents evaluate solely the context handed to them — they do
**not** discover sections or search for evidence.

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

`get_guideline` is the **only** governance MCP tool. It abstracts away where guidelines
physically live (local folders, Git, SharePoint, Confluence, DocuFind, …) so agents never
need to know the storage location. A single in-process MCP server is shared by all agents
(no per-domain server).

## Evidence model & provenance

Evidence is generated **directly during evaluation** from the extracted domain context, and
every `quote` is an **exact, verbatim** substring of that content (never paraphrased). Each
evaluator keeps **finding** (the conclusion), **reasoning** (why the evidence
satisfies/violates the guideline), and **evidence** (the exact quotes) distinct.

Every evidence item carries full **provenance** for auditability/reproducibility:
`section_header`, `line_range`, `guideline_domain`, `guideline_version`, `source_hash`, plus an
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
      "evidence": [ { "quote": "…exact SAD text…", "section_header": "2.4 Cross Functional Requirements", "line_range": "29-30",
                      "guideline_domain": "security", "guideline_version": "v1", "source_hash": "…",
                      "evidence_confidence": 0.98 } ] }
  ],
  "evidence": [ { "quote": "…exact SAD text…", "section_header": "2.4 Cross Functional Requirements", "line_range": "29-30",
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
name, evaluator model, and a short `scope` description (handed to the Governance Context
Agent so it can identify relevant content) live there, and `agents.py` and `schema.py`
derive from it. To add a domain (API, Cost, Cloud, …), add an entry to `DOMAIN_CONFIG` plus
`guidelines/<domain>/<version>/` — no other code changes.

## Project layout

    documents/*.md                          # SAD(s) under review
    guidelines/<domain>/<version>/          # guideline.md + examples.md (governance content)
    .claude/skills/governance-evaluation/   # behavior-only skill
    domains.py                              # DOMAIN_CONFIG — single source of truth (name/model/scope)
    tools.py                                # shared MCP server: get_guideline (the only governance tool)
    agents.py                               # sub-agent AgentDefinitions (governance-context, evaluators, synthesis) + orchestrator prompt
    schema.py                               # output shapes + Pydantic validation
    main_orchestrator.py                    # hashing, caching, launches the native orchestrator
    results/<doc>.json                      # final assessment (cache + audit record)

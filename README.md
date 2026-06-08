# SAD Governance Evaluation (Claude Agent SDK)

A model-driven framework that evaluates a **Solution Architecture Document (SAD)**
written in Markdown against governance guidelines, and produces an evidence-backed
governance assessment. Built on the **Claude Agent SDK**.

## How it works (model-driven)

A **single parent `query()`** is given three domain evaluators and a synthesis agent
as `AgentDefinition`s, plus the `Agent` tool. The **model** owns the workflow:

1. **Parse** the SAD into sections (by `##` headings).
2. **Route** each section to the relevant domain(s).
3. **Dispatch** to each evaluator subagent via the `Agent` tool, passing **both** the
   full SAD and the relevant section(s).
4. **Collect** the evaluators' results.
5. **Synthesize** — a synthesis subagent merges them, de-duplicates findings, and
   builds an evidence-linkage table.

The orchestrator **never evaluates the SAD itself** — it only parses, routes,
dispatches, collects, and triggers synthesis. There is no deterministic Python control
flow driving the evaluation; the agent does it.

```text
SAD Markdown
      ↓  parse sections → route → dispatch (Agent tool)
Data Movement Evaluator · Security Evaluator · Resilience Evaluator
      ↓  (each: get_guideline + find_evidence — the only two tools)
Evaluator results
      ↓
Synthesis  →  results/<doc>.json
              { "overall_status": ..., "evaluations": [...], "evidence": [...] }
```

## Domains

| Evaluator | Looks at |
|-----------|----------|
| **Data Movement** | data flow, pipelines, ingestion/export, storage, lineage, retention, PII movement |
| **Security** | authentication, authorization, encryption, secrets, network, access control |
| **Resilience** | availability/SLAs, redundancy/failover, disaster recovery, monitoring, scaling, degradation |

## Tools (exactly two)

Evaluators have only these tools:

- **`get_guideline(domain)`** — loads that domain's `guideline.md` **and** `examples.md`
  (both are used when evaluating). `domain` ∈ `data_movement`, `security`, `resilience`.
- **`find_evidence(markdown_document, query)`** — locates supporting text in the SAD and
  returns each match's section, line, and evidence text.

Both live in `tools.py` as one in-process MCP server (`governance`).

## Setup

    pip install -e .
    export ANTHROPIC_API_KEY=sk-ant-...

## Run

    governance-review                       # evaluate every documents/*.md
    governance-review documents/source.md   # evaluate one SAD
    # equivalently, without installing:
    python main_orchestrator.py [documents/source.md]

The final assessment is written to `results/<doc-stem>.json`.

## Guidelines & examples

Each domain owns its guidance; **both** files are loaded by the evaluator:

    guidelines/
        data_movement/  guideline.md  examples.md
        security/       guideline.md  examples.md
        resilience/     guideline.md  examples.md

`examples.md` is a first-class input — treated as part of the evaluator's knowledge.

## Output shape

```json
{
  "overall_status": "...",
  "evaluations": [
    { "domain": "Security", "score": 70, "rationale": "...", "findings": [ ... ] }
  ],
  "evidence": [
    { "quote": "...", "location": "Security, line 12", "supports": "..." }
  ]
}
```

Each evaluator returns `{ domain, score, rationale, evidence, findings }`; synthesis
merges these into the assessment above.

## Project layout

    documents/*.md                         # the SAD(s) under review (source.md included)
    guidelines/<domain>/guideline.md        # per-domain governance guideline
    guidelines/<domain>/examples.md         # per-domain examples (first-class input)
    tools.py                                # the two tools (get_guideline, find_evidence)
    agents.py                               # evaluator + synthesis AgentDefinitions, orchestrator prompt
    schema.py                               # evaluator result + final assessment shapes
    main_orchestrator.py                    # the single model-driven orchestrator (entry point)
    results/<doc>.json                      # generated governance assessment

## Scope

Governance evaluation only — no database persistence, external policy systems,
enterprise integrations, or generic compliance scanners. The previous generic
compliance tools (PII detection, secret scanning, user/email lookup, mock policy DBs,
external services) have been removed.

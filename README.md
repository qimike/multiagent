# Multi-Agent Document Governance (Claude Agent SDK)

A governance pipeline that reviews a Markdown design document against Security,
Data, and Resilient guidelines using independent Claude sub-agents, then synthesizes
a final report. Built on the **Claude Agent SDK**.

## Why this design

The orchestrator is **plain Python**, and each agent is an **isolated `query()`
call**. Every `query()` is its own session with `setting_sources=[]`, so each agent
gets a fresh context window and cannot see any other agent's prompt, guidelines, or
results. That enforces the architecture's core rule — *sub-agents do not talk to each
other* — at the context level, while keeping routing, the JSON schema, conflict
detection, and saved artifacts fully deterministic.

(An alternative that uses the SDK's *native* subagents is in
`orchestrator_native_subagents.py` — see "Two orchestration modes" below.)

## Prerequisites

- Python 3.10+
- Node.js 18+ (the SDK drives a bundled Claude Code CLI subprocess)
- An Anthropic API key (or a logged-in Claude subscription)

## Setup

    pip install -e .            # installs deps + the `governance-review` command
    # or: pip install -e ".[dev]"   to also get dev tools (ruff)
    export ANTHROPIC_API_KEY=sk-ant-...

Dependencies are declared in `pyproject.toml`.

## Run

    governance-review                      # batch over documents/*.md (cached)
    governance-review --force              # ignore the cache; re-test every document
    # equivalently, without installing:
    python main_orchestrator.py [--force]

The pipeline processes **every `documents/*.md`** and writes **one report per
document** to `results/<doc-stem>.json`:

    results/source.json   # for documents/source.md

Each report contains the three per-domain results, the synthesis output, plus
`source_file` and `content_hash`.

### Routing — one section, one agent (tag-based)

The three domains are **Security**, **Data**, and **Resilient**. Each `##` section
in a document is owned by **exactly one** agent, declared with a `[Tag]` in the
heading (case-insensitive, must match a domain):

    ## [Security] Authentication & Access
    ## [Data] Data Platform & Pipelines
    ## [Resilient] Operations

Rules:

- Every section goes to exactly one agent — no overlap. The `[Tag]` is stripped
  before the agent sees the heading.
- A section with **no tag**, or a tag that matches no domain, is routed to
  `DEFAULT_OWNER` (default `"Resilient"`, set in `main_orchestrator.py`) and listed
  in a **warning** after the routing summary.
- An agent that owns **no sections is skipped** (not called); it gets a
  `NOT_APPLICABLE` placeholder in the report so all three domains still appear.

There is intentionally no "give the whole document to an empty agent" fallback.

### Caching

Results are cached by filename with a content hash. On each run, for every
document:

- If `results/<stem>.json` exists and its stored `content_hash` matches the
  current file's hash, the cached report is returned and **no model is called**
  (prints `CACHE HIT`).
- If the file's content changed, it is **re-tested** and the report overwritten.
- `--force` re-tests everything regardless of the cache.

This gives "skip already-tested documents" and "run only the remaining ones" for
free when you drop new files into `documents/`.

## Project layout

    documents/*.md                # documents under review (source.md included)
    agents/<domain>/guidelines.md # what each domain agent checks against
    agents/<domain>/examples.md   # few-shot examples anchoring the JSON output
    agents/<domain>/tools.py      # per-domain custom tools (MCP server)
    shared_tools.py               # shared custom tool (MCP server) for all agents
    .claude/skills/<skill>/SKILL.md  # per-agent + shared review skills
    schema.py                     # shared output schema, validation, conflict detection
    agents.py                     # per-domain config + prompt builders + tool/skill wiring
    main_orchestrator.py          # PRIMARY: Python-driven, isolated agent calls
    orchestrator_native_subagents.py  # ALTERNATIVE: native SDK subagents
    architecture.mermaid          # diagram of the pipeline (cache + skills + tools)
    results/<doc>.json            # one generated report per document

## How it maps to the architecture

| Architecture concept            | Where it lives                                            |
|---------------------------------|-----------------------------------------------------------|
| read_markdown_file              | `read_markdown_file()` in main_orchestrator.py            |
| split_markdown_sections         | `split_markdown_sections()`                               |
| route by [Tag] (1 section/agent)| `routing_plan()` + `route_sections()` (tag-based)         |
| read_*_guidelines / examples    | `DomainAgent.load_context()` in agents.py                 |
| check_* domain checks           | the agent's reasoning, driven by guidelines + examples    |
| generate_conformance_result     | each agent returns the standard JSON (validated)          |
| validate_agent_output           | `validate_agent_output()` in schema.py                    |
| detect_conflict / log_exception | `detect_conflicts()` + the orchestrator's try/except      |
| Synthesis Agent                 | `run_synthesis_agent()` -> `synthesis` in `results/<doc>.json` |
| "sub-agents don't talk"         | each agent is a separate isolated session (no shared ctx) |

## Skills and tools

Each domain agent loads **skills** and may call **custom tools**:

- **Skills** live in `.claude/skills/<name>/SKILL.md` (a shared `conformance-common`
  plus one per domain: `security-review`, `data-review`, `resilient-review`). They
  carry the review procedure, guidelines, and output contract. Skills are only
  discovered when the agent runs with `setting_sources=["project"]` **and** has
  `"Skill"` in `allowed_tools` — both are set for the domain agents.
- **Custom tools** are defined with the `@tool` decorator and bundled into MCP
  servers via `create_sdk_mcp_server`: per-domain in `agents/<domain>/tools.py`
  (e.g. `check_secret_in_vault`, `check_pii_classification`, `check_record_exists`,
  `call_api`) plus a shared server in `shared_tools.py` (`policy_version`). Tool
  names follow `mcp__<server>__<tool>` and must appear in `allowed_tools`; the
  server is passed via `mcp_servers`. Because tools take multiple turns
  (call → result → reason), domain agents run with a higher `max_turns`.
  The implementations are clearly-marked **TODO placeholders** — wire them to real
  backends when ready. `call_api` imports `httpx` (a dependency in `pyproject.toml`) but makes
  no live request by default.

Skill names and tool servers are attached to each `DomainAgent` in `agents.py`
(`skills`, `tool_servers()`, `tool_names()`) and reused by both orchestrators.

## Two orchestration modes

1. **`main_orchestrator.py` (recommended).** Python decides routing and writes
   validated JSON. Deterministic, easy to test, reliable artifacts. Domain agents
   run in parallel.

2. **`orchestrator_native_subagents.py`.** A single parent `query()` is given four
   `AgentDefinition`s and the `Agent` tool; the model decides when to call each
   subagent. Less glue code, but routing and file output are model-driven and less
   predictable. Subagents are one level deep (they can't spawn their own).

## Extending

- **MVP staging:** trim `DOMAIN_AGENTS` in `agents.py` to just Security + Data first,
  then add Resilient, then tighten `detect_conflicts()`. Adding a domain also means
  adding it to `schema.py`'s `DOMAINS` and giving its sections a `[Tag]`.
- **Resilient agent:** its `guidelines.md`/`examples.md` and the `resilient-review`
  skill still carry placeholder (ex-Business) criteria — see their TODOs to rewrite
  them for resilience (SLAs, failover/DR, incident response, monitoring, etc.).
- **Per-agent models:** change the `model` field per `DomainAgent` (e.g., `opus` for
  Security, `haiku` for a cheap first pass).
- **Better routing:** replace the keyword classifier in `classify_section_domain()`
  with an LLM classification call — nothing else changes.
- **Persistence/memory:** these agents are intentionally stateless per run. If you
  want an agent to remember across runs, resume its session or give it a Memory-tool
  namespace; keep namespaces distinct per agent so memory stays unshared.

## Cost note

Each domain agent is a separate Claude instance with its own context, so a 3-agent +
synthesis run is roughly 4 model calls per document. Multi-agent setups consume
materially more tokens than a single call — size your plan or API budget accordingly,
especially if you process many documents.

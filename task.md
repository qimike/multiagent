# Refactor Repository to Claude Native Sub-Agent Architecture

Refactor this repository to use Claude SDK Native Sub-Agents as the primary execution model while preserving deterministic document structure processing.

The final architecture should be:

Source Markdown File
→ SHA256 Hash
→ Cache Check
→ Deterministic Section Parser
→ Claude Native Orchestrator
→ Domain Sub-Agents
→ Synthesis Agent
→ JSON Output

---

# Core Principles

1. Claude Native Sub-Agents should be the primary execution model.

2. Remove Python-managed agent routing and orchestration.

3. Keep deterministic markdown parsing.

4. Governance content must be externalized from Skills.

5. Use a single shared MCP server.

6. Preserve structured JSON output.

---

# Deterministic Section Parsing

Markdown section discovery must be deterministic.

Example:

# Overview

# Data Flow

# Security

# Resilience

Create a parser that extracts sections based on markdown headers.

The parser should produce a routing map:

{
"Data Flow": "data_movement",
"Security": "security",
"Resilience": "resilience",
}

IMPORTANT:

Agents must NOT discover their own sections.

Agents must NOT determine section ownership.

Section ownership must be determined by the markdown parser.

Claude agents should only evaluate sections assigned to them.

This requirement is mandatory.

---

# SHA256 Tracking

Calculate SHA256 for every source document.

Example:

source.md

↓

SHA256

↓

source_hash

Store source_hash in:

- cache
- intermediate outputs
- final outputs

Example:

{
"source_file": "source.md",
"source_hash": "abc123..."
}

---

# Cache

Before evaluation:

1. Calculate source_hash.
2. Check cache.
3. If cached result exists:
   return cached result.
4. Otherwise:
   continue evaluation.

Cache key should include:

source_hash

- guideline_version

This ensures guideline updates invalidate stale results.

---

# Guideline Repository

Replace current guideline storage with versioned guidelines.

Structure:

guidelines/

```
data_movement/
    v1/
        guideline.md
        examples.md

security/
    v1/
        guideline.md
        examples.md

resilience/
    v1/
        guideline.md
        examples.md

```

The design must support:

v1
v2
v3

without requiring Skill changes.

---

# Skills

Skills should contain:

- evaluation behavior
- reasoning strategy
- output formatting

Skills should NOT contain governance content.

Skills must dynamically load:

guideline.md

and optionally:

examples.md

for the active version.

Example:

Data Movement Skill

↓

guidelines/data_movement/v1/guideline.md

---

# MCP Architecture

Use one shared MCP server.

Do NOT create a separate MCP server per domain.

Lifecycle:

Application Start

↓

Start Shared MCP Server

↓

Register All Tools

↓

Run Orchestrator

↓

Run Domain Agents

↓

Run Synthesis

↓

Shutdown MCP Server

All agents should use the same MCP server.

---

# Evidence Retrieval

Current evidence retrieval is too similar to keyword matching.

Replace with semantic retrieval.

Preferred order:

1. Hybrid Retrieval
2. BM25
3. Embedding Search

Evidence output must include:

{
"evidence_text": "...",
"section": "Data Flow",
"confidence": 0.92
}

---

# Evidence Provenance

Every evidence item must include:

{
"section": "Data Flow",
"line_range": "120-145",
"guideline_domain": "data_movement",
"guideline_version": "v1",
"source_hash": "abc123..."
}

This is required for auditability.

---

# Claude Native Sub-Agents

Use Claude SDK AgentDefinition.

Examples:

- Data Movement Agent
- Security Agent
- Resilience Agent

The orchestrator should delegate evaluation to these agents.

The orchestrator should not perform domain evaluation itself.

---

# Synthesis Agent

Create a dedicated synthesis agent.

Responsibilities:

- collect all agent outputs
- merge findings
- calculate final result
- consolidate evidence
- generate final JSON

---

# Output Schema

Final output must include:

{
"source_file": "...",
"source_hash": "...",

```
"guideline_domain": "...",
"guideline_version": "v1",

"evaluation_result": "...",

"confidence": 0.95,

"evidence": [...]
```

}

---

# Deliverable

Refactor the repository directly.

Update all affected code.

Remove obsolete deterministic orchestration code.

Preserve deterministic markdown parsing and deterministic section ownership.

Claude Native Sub-Agents should become the primary execution model.

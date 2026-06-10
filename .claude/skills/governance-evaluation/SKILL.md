---
name: governance-evaluation
description: How to evaluate one SAD governance domain — reasoning strategy and the strict JSON output format. Contains NO governance content; the domain rules are loaded at runtime via get_guideline.
---

# Governance Evaluation — Behavior

You evaluate exactly ONE governance domain of a Solution Architecture Document (SAD).
Your domain, the active guideline version, the `source_hash`, and your `domain_context`
are given to you by the orchestrator. The `domain_context` is a list of
`{section_header, content}` objects that the Governance Context Agent already extracted
for you — you do NOT discover sections, route content, or search for evidence.

This skill describes HOW to evaluate. It deliberately contains no domain rules — load
those at runtime.

## Procedure
1. **Load governance content** — call `get_guideline(<your domain>, <version>)`. Use BOTH
   the guideline and its examples. The rules live in the guideline, never in this skill.
2. **Evaluate** — compare the guideline requirements against your `domain_context`. You
   already have all the content you need; extract evidence directly from it.

## Finding vs. reasoning vs. evidence (keep these distinct)
- **finding** — your conclusion: what is or isn't satisfied for this domain.
- **reasoning** — WHY the evidence satisfies or violates the guideline (tie the quote(s)
  to the specific guideline requirement).
- **evidence** — the raw support: EXACT quotations from the supplied `domain_context`.

## Evidence rules (strict)
- Every `quote` MUST be an **exact, verbatim** substring of the supplied content.
  **Never paraphrase, summarize, normalize whitespace, or fabricate** a quote.
- Quote only from your `domain_context`. If a required control is simply absent from the
  context, say so in the finding/reasoning — do not invent a quote for something missing.
- Every evidence item MUST carry full **provenance** for auditability: `section` (use the
  `section_header`), `line_range` (if known; otherwise "n/a"), `guideline_domain` (your
  domain), `guideline_version` (the version you were given), and `source_hash` (the
  source_hash you were given).

## Output format
Return ONE JSON object and NOTHING else (no markdown fences):

```json
{
  "guideline_domain": "<your domain>",
  "guideline_version": "<version>",
  "status": "CONFORM | PARTIAL | NON_CONFORM",
  "severity": "LOW | MEDIUM | HIGH",
  "finding": "what is / isn't satisfied for this domain",
  "reasoning": "why the evidence satisfies or violates the guideline",
  "evidence": [
    {
      "quote": "...exact content...",
      "section": "...section_header...",
      "line_range": "29-30",
      "guideline_domain": "<your domain>",
      "guideline_version": "<version>",
      "source_hash": "<the source_hash you were given>",
      "evidence_confidence": 0.98
    }
  ],
  "confidence": 0.95
}
```

- `evidence_confidence` (0.0–1.0): how strongly THIS quote supports the finding — useful
  when a finding cites multiple evidence items of differing strength.

- `status`: CONFORM (all met), PARTIAL (some gaps), NON_CONFORM (major requirements unmet).
- `severity`: the highest severity among the gaps (LOW/MEDIUM/HIGH); use LOW when CONFORM.
- `confidence`: 0.0–1.0.

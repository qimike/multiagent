---
name: governance-evaluation
description: How to evaluate one SAD governance domain — reasoning strategy, tool usage, and the strict JSON output format. Contains NO governance content; the domain rules are loaded at runtime via get_guideline.
---

# Governance Evaluation — Behavior

You evaluate exactly ONE governance domain of a Solution Architecture Document (SAD).
Your domain, the active guideline version, the `source_hash`, and your assigned
section(s) are given to you by the orchestrator. You do NOT choose your own sections.

This skill describes HOW to evaluate. It deliberately contains no domain rules — load
those at runtime.

## Procedure
1. **Load governance content** — call `get_guideline(<your domain>, <version>)`. Use BOTH
   the guideline and its examples. The rules live in the guideline, never in this skill.
2. **Focus** on your assigned section(s); use the rest of the SAD only for context.
3. **Gather evidence** — for the points that matter, call
   `find_evidence(<full SAD markdown>, <query>)` and use the returned
   `evidence_text` / `section` / `line_range` / `confidence`.
4. **Judge** conformance against each requirement and record findings for gaps.

## Reasoning strategy
- Prefer evidence from your assigned section(s). If a required control is simply absent,
  that absence is itself a finding — do not fabricate evidence.
- Tie every finding to a guideline requirement, and where possible to retrieved evidence.
- Severity: HIGH (security / regulatory / data-loss / availability risk), MEDIUM, LOW.

## Output format
Return ONE JSON object and NOTHING else (no markdown fences):

```json
{
  "guideline_domain": "<your domain>",
  "guideline_version": "<version>",
  "evaluation_result": "COMPLIANT | PARTIALLY_COMPLIANT | NON_COMPLIANT",
  "confidence": 0.0,
  "rationale": "short justification",
  "findings": [
    { "issue": "...", "severity": "HIGH | MEDIUM | LOW", "recommendation": "..." }
  ],
  "evidence": [
    {
      "evidence_text": "...",
      "section": "...",
      "line_range": "23-23",
      "confidence": 0.0,
      "guideline_domain": "<your domain>",
      "guideline_version": "<version>",
      "source_hash": "<the source_hash you were given>"
    }
  ]
}
```

Every evidence item MUST carry full provenance (`section`, `line_range`,
`guideline_domain`, `guideline_version`, `source_hash`) for auditability.

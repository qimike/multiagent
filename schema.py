"""Output shapes for the SAD governance-evaluation framework.

These example objects are injected into the agent prompts so the model emits the exact
target shapes. There is no Python-side validation step — the Claude native sub-agents
produce the JSON; these shapes are the contract.

Evidence is produced directly during evaluation and must be an EXACT quotation from
the SAD source text (never paraphrased). `find_evidence` is an optional helper, not a
required step.
"""

from __future__ import annotations

from typing import Any

# The governance domains (kept in sync with parser.DOMAINS).
DOMAINS = ("data_movement", "security", "resilience")

ACTIVE_GUIDELINE_VERSION = "v1"

# Conformance status enum used by evaluators and the overall result.
STATUS_VALUES = ("CONFORM", "PARTIAL", "NON_CONFORM")
SEVERITY_VALUES = ("LOW", "MEDIUM", "HIGH")

# What each domain evaluator returns. `finding`, `reasoning`, and `evidence` are
# distinct: the finding is the conclusion, the reasoning explains why the evidence
# satisfies/violates the guideline, and each evidence item is an exact SAD quote.
EVALUATOR_RESULT_EXAMPLE: dict[str, Any] = {
    "guideline_domain": "security",
    "guideline_version": "v1",
    "status": "PARTIAL",
    "severity": "HIGH",
    "finding": "Secrets management and encryption-at-rest requirements are not met: "
    "database credentials are stored in plain configuration files and rotated manually.",
    "reasoning": "The Secrets Management guideline requires credentials to live in an "
    "approved vault with automated rotation; the quoted text shows config-file storage "
    "with manual quarterly rotation, which violates that requirement.",
    "evidence": [
        {
            "quote": "Database credentials are currently stored in application configuration files and rotated manually each quarter.",
            "section": "Security",
            "line_range": "29-30",
        }
    ],
    "confidence": 0.9,
}

# What the synthesis agent returns / the orchestrator writes — the final assessment.
# Top level carries source_file, source_hash, guideline_version, the overall result +
# confidence, the per-domain evaluations, and consolidated evidence.
FINAL_OUTPUT_EXAMPLE: dict[str, Any] = {
    "source_file": "source.md",
    "source_hash": "abc123...",
    "guideline_version": "v1",
    "evaluation_result": "NON_CONFORM",
    "confidence": 0.9,
    "evaluations": [EVALUATOR_RESULT_EXAMPLE],
    "evidence": [
        {
            "quote": "Database credentials are currently stored in application configuration files and rotated manually each quarter.",
            "section": "Security",
            "line_range": "29-30",
        }
    ],
}

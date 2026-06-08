"""Output shapes for the SAD governance-evaluation framework.

These example objects are injected into the agent prompts so the model emits the exact
target shapes. There is no Python-side validation step — the agents (Claude native
sub-agents) produce the JSON; these shapes are the contract.
"""

from __future__ import annotations

from typing import Any

# The governance domains (kept in sync with parser.DOMAINS).
DOMAINS = ("data_movement", "security", "resilience")

ACTIVE_GUIDELINE_VERSION = "v1"

# What each domain evaluator returns.
EVALUATOR_RESULT_EXAMPLE: dict[str, Any] = {
    "guideline_domain": "security",
    "guideline_version": "v1",
    "evaluation_result": "PARTIALLY_COMPLIANT",
    "confidence": 0.85,
    "rationale": "Authentication and TLS are covered; encryption at rest and secrets "
    "management are not.",
    "findings": [
        {
            "issue": "Database credentials are stored in plain config files.",
            "severity": "HIGH",
            "recommendation": "Move credentials to an approved secrets vault with rotation.",
        }
    ],
    "evidence": [
        {
            "evidence_text": "Database credentials are currently stored in application "
            "configuration files and rotated manually each quarter.",
            "section": "Security",
            "line_range": "29-30",
            "confidence": 0.92,
            "guideline_domain": "security",
            "guideline_version": "v1",
            "source_hash": "abc123...",
        }
    ],
}

# What the synthesis agent returns / the orchestrator writes — the final assessment.
# Top level carries source_file, source_hash, guideline_version, the overall
# evaluation_result + confidence, the per-domain evaluations, and consolidated evidence.
FINAL_OUTPUT_EXAMPLE: dict[str, Any] = {
    "source_file": "source.md",
    "source_hash": "abc123...",
    "guideline_version": "v1",
    "evaluation_result": "NON_COMPLIANT",
    "confidence": 0.8,
    "evaluations": [EVALUATOR_RESULT_EXAMPLE],
    "evidence": [EVALUATOR_RESULT_EXAMPLE["evidence"][0]],
}

"""Output shapes for the SAD governance-evaluation framework.

These example objects are injected verbatim into the evaluator and synthesis agent
prompts so the model emits the exact target shape. The flow is model-driven (a single
parent query() delegating to subagents via the Agent tool), so there is no Python-side
validation step — these shapes are the contract.
"""

from __future__ import annotations

from typing import Any

# The three SAD governance domains.
DOMAINS = ("Data Movement", "Security", "Resilience")

# What each domain evaluator returns.
EVALUATOR_RESULT_EXAMPLE: dict[str, Any] = {
    "domain": "Security",
    "score": 70,
    "rationale": "Authentication and TLS are well covered; encryption at rest and "
    "secrets management are not addressed.",
    "evidence": [
        {
            "section": "Security",
            "quote": "All API access requires OAuth2 via the corporate IdP.",
            "location": "Security, line 12",
        }
    ],
    "findings": [
        {
            "issue": "Encryption at rest is not documented.",
            "severity": "HIGH",
            "recommendation": "Document encryption at rest for all sensitive data stores.",
        }
    ],
}

# What the synthesis layer returns — the final governance assessment.
FINAL_ASSESSMENT_EXAMPLE: dict[str, Any] = {
    "overall_status": "PARTIALLY_COMPLIANT",
    "evaluations": [
        {
            "domain": "Security",
            "score": 70,
            "rationale": "....",
            "findings": [
                {
                    "issue": "Encryption at rest is not documented.",
                    "severity": "HIGH",
                    "recommendation": "Document encryption at rest.",
                }
            ],
        }
    ],
    "evidence": [
        {
            "quote": "All API access requires OAuth2 via the corporate IdP.",
            "location": "Security, line 12",
            "supports": "Security — authentication is conformant",
        }
    ],
}

"""Output shapes + runtime validation for the SAD governance-evaluation framework.

The example objects are injected into the agent prompts so the model emits the exact
target shapes. The Pydantic models validate the final written output at runtime, so a
missing field / malformed structure is caught instead of silently shipping.

Evidence is produced directly during evaluation and must be an EXACT quotation from the
SAD source text (never paraphrased). Every evidence item carries full provenance
(guideline_domain, guideline_version, source_hash) for auditability.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from domains import DOMAINS  # single source of truth

ACTIVE_GUIDELINE_VERSION = "v1"

# Conformance status enum used by evaluators and the overall result.
STATUS_VALUES = ("CONFORM", "PARTIAL", "NON_CONFORM")
SEVERITY_VALUES = ("LOW", "MEDIUM", "HIGH")


# ---------------------------------------------------------------------------
# Example shapes (injected into prompts)
# ---------------------------------------------------------------------------
_EVIDENCE_EXAMPLE: dict[str, Any] = {
    "quote": "Database credentials are currently stored in application configuration files and rotated manually each quarter.",
    "section": "Security",
    "line_range": "29-30",
    "guideline_domain": "security",
    "guideline_version": "v1",
    "source_hash": "abc123...",
    "evidence_confidence": 0.98,
}

EVALUATOR_RESULT_EXAMPLE: dict[str, Any] = {
    "guideline_domain": "security",
    "guideline_version": "v1",
    "status": "PARTIAL",
    "severity": "HIGH",
    "finding": "Secrets management and encryption-at-rest requirements are not met: "
    "database credentials are stored in plain configuration files and rotated manually.",
    "reasoning": "The Secrets Management guideline requires credentials in an approved "
    "vault with automated rotation; the quoted text shows config-file storage with manual "
    "rotation, which violates that requirement.",
    "evidence": [_EVIDENCE_EXAMPLE],
    "confidence": 0.9,
}

FINAL_OUTPUT_EXAMPLE: dict[str, Any] = {
    "source_file": "source.md",
    "source_hash": "abc123...",
    "guideline_version": "v1",
    "evaluation_result": "NON_CONFORM",
    "confidence": 0.9,
    "evaluations": [EVALUATOR_RESULT_EXAMPLE],
    "evidence": [_EVIDENCE_EXAMPLE],
}


# ---------------------------------------------------------------------------
# Runtime validation (Pydantic) — applied to the final written output
# ---------------------------------------------------------------------------
class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="allow")  # tolerate extra keys, require these
    quote: str
    section: str
    line_range: str
    guideline_domain: str
    guideline_version: str
    source_hash: str
    # Per-evidence confidence — how strongly this quote supports the finding.
    evidence_confidence: float | None = None


class EvaluatorResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    guideline_domain: str
    guideline_version: str
    status: Literal["CONFORM", "PARTIAL", "NON_CONFORM"]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    finding: str
    reasoning: str
    evidence: list[EvidenceItem]
    confidence: float


class FinalOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_file: str
    source_hash: str
    guideline_version: str
    evaluation_result: Literal["CONFORM", "PARTIAL", "NON_CONFORM"]
    confidence: float
    evaluations: list[EvaluatorResult]
    evidence: list[EvidenceItem]


def validate_final_output(data: dict) -> FinalOutput:
    """Validate the final assessment dict; raises pydantic.ValidationError if malformed."""
    return FinalOutput.model_validate(data)

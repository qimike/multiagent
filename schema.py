"""Standard output schema shared by every domain agent, plus validation and
conflict-detection helpers used by the orchestrator.

Every domain agent (Security / Data / Resilient) must return JSON in exactly this
shape so the Synthesis Agent and the orchestrator can treat them uniformly.
"""

from __future__ import annotations

from typing import Any

DOMAINS = ("Security", "Data", "Resilient")

STATUS_VALUES = (
    "COMPLIANT",
    "PARTIALLY_COMPLIANT",
    "NON_COMPLIANT",
    "NOT_APPLICABLE",
)

# The canonical example, injected verbatim into every agent prompt so the model
# sees the exact target shape.
OUTPUT_SCHEMA_EXAMPLE: dict[str, Any] = {
    "domain": "Security",
    "status": "PARTIALLY_COMPLIANT",
    "conformance_score": 78,
    "evidence": [
        {
            "source_text": "The system uses OAuth2.",
            "guideline": "All APIs must use approved authentication.",
            "assessment": "Compliant",
        }
    ],
    "violations": [
        {
            "guideline": "Secrets must be stored in approved vault.",
            "reason": "No secrets management approach was documented.",
        }
    ],
    "recommendations": [
        "Add secrets management design using approved vault.",
    ],
    "confidence": 0.9,
    "exceptions": [],
}


def validate_agent_output(data: Any) -> list[str]:
    """Return a list of human-readable schema errors. Empty list == valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Output is not a JSON object."]

    if data.get("domain") not in DOMAINS:
        errors.append(f"'domain' must be one of {DOMAINS}, got {data.get('domain')!r}")

    if data.get("status") not in STATUS_VALUES:
        errors.append(f"'status' must be one of {STATUS_VALUES}, got {data.get('status')!r}")

    score = data.get("conformance_score")
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        errors.append("'conformance_score' must be a number between 0 and 100")

    conf = data.get("confidence")
    if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
        errors.append("'confidence' must be a number between 0 and 1")

    for field in ("evidence", "violations", "recommendations", "exceptions"):
        if not isinstance(data.get(field), list):
            errors.append(f"'{field}' must be a list")

    return errors


def detect_conflicts(results: list[dict]) -> list[dict]:
    """Lightweight cross-domain conflict detection for the MVP.

    Flags two situations:
      1. The same source_text is assessed differently by two domains.
      2. Two confident domains report widely diverging conformance scores.
    Extend this with your own rules as the pipeline matures.
    """
    conflicts: list[dict] = []

    # 1. contradictory assessments of the same source text
    seen: dict[str, tuple[str, str]] = {}  # normalized text -> (domain, assessment)
    for r in results:
        domain = r.get("domain", "Unknown")
        for ev in r.get("evidence", []) or []:
            text = (ev.get("source_text") or "").strip().lower()
            assessment = (ev.get("assessment") or "").strip().lower()
            if not text:
                continue
            if text in seen and seen[text][1] != assessment:
                conflicts.append(
                    {
                        "type": "contradictory_assessment",
                        "source_text": ev.get("source_text"),
                        "domains": [seen[text][0], domain],
                        "assessments": [seen[text][1], assessment],
                    }
                )
            else:
                seen[text] = (domain, assessment)

    # 2. diverging conformance scores between two confident domains
    scored = [
        (r.get("domain"), r.get("conformance_score"), r.get("confidence", 0))
        for r in results
        if isinstance(r.get("conformance_score"), (int, float))
    ]
    for i in range(len(scored)):
        for j in range(i + 1, len(scored)):
            d1, s1, c1 = scored[i]
            d2, s2, c2 = scored[j]
            if abs(s1 - s2) > 40 and c1 >= 0.7 and c2 >= 0.7:
                conflicts.append(
                    {
                        "type": "score_divergence",
                        "domains": [d1, d2],
                        "scores": [s1, s2],
                    }
                )

    return conflicts

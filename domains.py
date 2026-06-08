"""Single source of truth for governance domains.

parser.py (routing), agents.py (evaluator definitions), schema.py (domain list), and
tools.py (guideline lookup) all derive from DOMAIN_CONFIG, so adding a domain (API, Cost,
Cloud, Observability, …) is a one-place change here plus its guidelines/<domain>/<ver>/.
"""

from __future__ import annotations

# key -> config. `routing` is a case-insensitive regex matched against section headings
# by the deterministic parser; `name` is the display name; `model` is the evaluator model.
DOMAIN_CONFIG: dict[str, dict] = {
    "data_movement": {
        "name": "Data Movement",
        "model": "opus",
        # Priority 1: also catch event-streaming / messaging / queue / Kafka phrasing.
        # ("messag" matches message/messaging/messages; "stream" matches streaming.)
        "routing": r"data\s*flow|data\s*movement|pipeline|ingest|etl|integration|event|stream|messag|queue|kafka",
    },
    "security": {
        "name": "Security",
        "model": "opus",
        "routing": r"security|auth|access|encryption|secret",
    },
    "resilience": {
        "name": "Resilience",
        "model": "opus",
        "routing": r"resilien|availab|reliab|operations|disaster|failover|sla",
    },
}

# Ordered tuple of domain keys.
DOMAINS = tuple(DOMAIN_CONFIG.keys())

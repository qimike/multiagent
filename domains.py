"""Single source of truth for governance domains.

agents.py (evaluator + section-assignment definitions), schema.py (domain list), and
tools.py (guideline lookup) all derive from DOMAIN_CONFIG, so adding a domain (API, Cost,
Cloud, Observability, …) is a one-place change here plus its guidelines/<domain>/<ver>/.

Section ownership is NOT decided here (or anywhere in Python). The `scope` line is a short,
human-readable description of what each domain cares about; it is handed to the Claude
native section-assignment agent so it can reason about which sections belong to which
domain. It is NOT a routing rule — Claude decides ownership semantically.
"""

from __future__ import annotations

# key -> config. `name` is the display name; `model` is the evaluator model; `scope` is a
# short description of the domain's concerns, surfaced to the section-assignment agent.
DOMAIN_CONFIG: dict[str, dict] = {
    "data_movement": {
        "name": "Data Movement",
        "model": "opus",
        "scope": "source systems, target systems, data flow, transformation, lineage, "
        "retention, and archival process",
    },
    "security": {
        "name": "Security",
        "model": "opus",
        "scope": "authentication, authorization, RBAC, encryption, network controls, "
        "service principals, and private endpoints",
    },
    "resilience": {
        "name": "Resilience",
        "model": "opus",
        "scope": "RTO, RPO, retry strategy, failover, replication, disaster recovery, "
        "and availability",
    },
}

# Ordered tuple of domain keys.
DOMAINS = tuple(DOMAIN_CONFIG.keys())

---
name: resilient-review
description: Resilient-domain conformance guidelines and review procedure — SLAs/SLOs, failover & redundancy, disaster recovery, incident response, monitoring/alerting, autoscaling, and graceful degradation. Load this when assessing a section for Resilient conformance.
---

# Resilient Conformance Review

Assess the section ONLY for Resilience concerns. Follow `conformance-common` for the
procedure and output contract.

> **TODO — REWRITE FOR RESILIENCE.** The criteria below are placeholders inherited
> from the former Business agent. Replace them with real resilience criteria:
>
> - **Availability targets** — SLAs/SLOs defined (uptime, latency) with owners.
> - **Failover & redundancy** — no single points of failure; multi-AZ/region as needed.
> - **Disaster recovery** — backups, restore tests, RTO/RPO defined.
> - **Incident response** — on-call, runbooks, escalation paths documented.
> - **Monitoring & alerting** — health checks, metrics, and alert coverage.
> - **Scalability & degradation** — autoscaling, load limits, graceful degradation.
>
> Until rewritten, the placeholder guidelines are:

## Capability Alignment (placeholder)
- The solution MUST map to a named business capability or strategic objective.

## Stakeholder Mapping (placeholder)
- Sponsor and primary stakeholders MUST be identified, with their interest stated.

## Operational Impact (placeholder)
- Operational ownership, SLAs, and support model SHOULD be described.
- Impact on existing processes SHOULD be noted.

## Tool use
When the design references an external system or endpoint whose status would change
your assessment, you may call `call_api` to probe it (a placeholder; see the domain's
tools.py TODO for resilience-specific tools). Treat its result as supporting evidence.

## Worked examples (placeholder — replace with resilience examples)
- "There is no documented SLA or incident runbook for the new API yet." → violation
  "operational ownership, SLAs, and support model should be described" → recommend
  defining an SLA and an incident runbook before go-live.

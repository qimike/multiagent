# Resilient Few-Shot Examples

> **TODO — REWRITE FOR RESILIENCE.** These examples still illustrate the old
> business-alignment checks. Replace them with resilience examples (e.g. SLA/SLO
> defined vs. missing, failover/DR documented vs. single-point-of-failure, runbook
> present vs. absent) once the guidelines are rewritten.

## Example A — capability alignment present (compliant)
Section text: "Supports the Unified Customer Experience capability, sponsored by the
VP of Customer Operations."
- evidence: capability + sponsor named → "Capability alignment" / "Stakeholder
  mapping" → "Compliant".

## Example B — benefits stated but no KPIs (partial)
Section text: "Expected benefit is faster case resolution and fewer duplicates."
- evidence: qualitative benefit → "Business case" → "Partial".
- violation: "Benefits should include measurable target KPIs/OKRs" → reason
  "Benefits are qualitative; no measurable targets are defined."
- recommendation: "Add target KPIs (e.g., reduction in average handle time)."

## Example C — no ROI / cost-benefit (violation)
Section text: "A formal cost-benefit analysis has not been included."
- violation: "A cost-benefit or ROI consideration should be included" → reason
  "No cost-benefit analysis is provided."
- recommendation: "Add a high-level cost-benefit summary to support prioritization."

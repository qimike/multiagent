# Resilience Examples

## Example A — SLA and redundancy present (conformant)
SAD text: "99.9% availability SLA; the service runs across three AZs with automatic
failover."
- evidence: "99.9% availability SLA" + "three AZs with automatic failover" →
  "Availability Targets" / "Redundancy & Failover" → conformant.

## Example B — no SLA / runbook (violation)
SAD text: "There is no documented SLA or incident runbook for the new API yet."
- finding: issue "No SLA/SLO and no incident runbook defined", severity HIGH,
  recommendation "Define availability/latency SLOs and an incident runbook with
  escalation paths before go-live."

## Example C — no disaster recovery (violation)
SAD text: "Backups and recovery objectives are not described."
- finding: issue "No backup/DR strategy or RTO/RPO", severity HIGH,
  recommendation "Define backups, test restores, and document RTO/RPO for critical
  data and services."

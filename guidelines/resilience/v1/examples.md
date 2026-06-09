# Resilience Examples

These illustrate how to map SAD text to the guideline and phrase evidence/findings. They
are illustrative — do not assume any specific section numbering.

## Example A — availability and recovery objectives stated (conformant)
SAD text: "Platform Uptime: 99.9% … RTO: 30 minutes … RPO: Zero data loss."
- evidence: "99.9%" → "Availability"; "RTO: 30 minutes" + "RPO: Zero data loss" →
  "Recovery Objectives" → objectives are defined.
- finding: when "Zero data loss" (RPO=0) is claimed, confirm the replication mechanism that
  achieves it is identified.

## Example B — replication and failover across layers (conformant)
SAD text: "ADF Automatic Retry … Azure SQL Geo Replication … Snowflake Cross Region
Replication … ADLS ZRS / GRS."
- evidence: "Automatic Retry" → "Retry Strategy"; "Geo Replication" + "Cross Region
  Replication" + "ZRS / GRS" → "Replication" / "Failover" addressed per layer → conformant.

## Example C — DR/runbook gap (partial/violation)
SAD text: replication is listed but no disaster-recovery runbook or restore test is
described.
- finding: issue "No documented, testable disaster-recovery procedure tying replication to
  the stated RTO/RPO", severity HIGH, recommendation "Document a DR approach with testable
  restore that meets the RTO/RPO, including escalation/runbook."

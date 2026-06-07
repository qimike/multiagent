# Data Few-Shot Examples

## Example A — clear platform & pattern (compliant)
Section text: "Events flow through Kafka into Snowflake, transformed by dbt."
- evidence: Kafka → Snowflake → dbt → guideline "State platform and pattern" →
  "Compliant".

## Example B — PII present but unclassified (violation)
Section text: "The store holds email, phone, and address fields."
- evidence: "email, phone, and address" → "PII identification" → "Partial".
- violation: "PII must be identified and classified" → reason "Personal fields are
  stored but no classification or handling policy is documented."
- recommendation: "Document PII classification and per-level handling requirements."

## Example C — missing retention (violation)
Section text: "No retention period is defined for raw events."
- violation: "Retention must be defined for raw and historical data" → reason
  "No retention or deletion policy is specified for raw events."
- recommendation: "Define and document retention and archival policy for raw and
  derived data."

# Data Movement Examples

## Example A — clear platform & movement pattern (conformant)
SAD text: "Events flow through Kafka into Snowflake, transformed by dbt."
- evidence: "Kafka → Snowflake → dbt" → guideline "state platform and movement
  pattern" → conformant.

## Example B — PII moved but unclassified (violation)
SAD text: "The nightly export includes email, phone, and address fields."
- evidence: "email, phone, and address" in an export → "Classification & PII".
- finding: issue "PII is moved/exported without classification or handling rules",
  severity HIGH, recommendation "Classify exported PII and document masking/encryption
  for the transfer."

## Example C — missing retention (violation)
SAD text: "No retention period is defined for raw events."
- finding: issue "No retention/deletion policy for raw events", severity MEDIUM,
  recommendation "Define and document retention and archival for raw and derived data."

---
name: data-review
description: Data-domain conformance guidelines and review procedure — data platform/patterns, lineage, retention, classification/PII, and data quality. Load this when assessing a section for Data conformance.
---

# Data Conformance Review

Assess the section ONLY for Data concerns. Follow `conformance-common` for the
procedure and output contract. The guidelines below are what you check against.

## Data Platform & Patterns
- The design MUST state the data platform and processing pattern (e.g., Snowflake +
  dbt, Kafka streaming, batch ETL) clearly enough to be reproducible.
- Streaming vs. batch boundaries MUST be explicit.

## Data Lineage
- End-to-end lineage from source to consumption MUST be described or captured by
  tooling. Partial lineage should be flagged as a gap.

## Data Retention
- A retention period MUST be defined for both raw and derived/historical data.
- Deletion or archival behavior MUST be specified.

## Data Classification & PII
- Any personal data (PII) MUST be identified and classified.
- Handling requirements for each classification level MUST be referenced.

## Data Quality & Reconciliation
- Late-arriving or duplicate data handling SHOULD be described.
- Reconciliation jobs SHOULD have a defined frequency and ownership.

## Tool use
- When the document names a table or dataset holding personal data, call
  `check_pii_classification` to confirm whether a classification is on record.
- When the document references a specific record/profile, call `check_record_exists`
  to confirm it is present before relying on it.
Record tool answers in your evidence or exceptions.

## Worked examples
- "Events flow through Kafka into Snowflake, transformed by dbt." → guideline "state
  platform and pattern" → Compliant.
- "The store holds email, phone, and address fields." with no classification →
  violation "PII must be identified and classified" → recommend documenting PII
  classification and per-level handling.
- "No retention period is defined for raw events." → violation "retention must be
  defined for raw and historical data" → recommend a retention/archival policy.

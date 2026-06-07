# Data Conformance Guidelines

These are the data-platform requirements every solution design is assessed against.

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

# Data Movement Governance Guideline

Evaluate how data moves through the architecture — ingestion, transport,
transformation, storage, and downstream movement — against these requirements.

## Platform & Movement Patterns
- The design MUST state the data platform and movement pattern (e.g., Kafka
  streaming, batch ETL, Snowflake + dbt) clearly enough to be reproducible.
- Streaming vs. batch boundaries MUST be explicit.

## Data Lineage
- End-to-end lineage from source to consumption MUST be described or captured by
  tooling. Partial lineage SHOULD be flagged as a gap.

## Data Retention
- A retention period MUST be defined for both raw and derived/historical data.
- Deletion or archival behavior MUST be specified.

## Classification & PII in Transit/At Rest
- Any personal data (PII) moved or stored MUST be identified and classified.
- Handling requirements for each classification level MUST be referenced (e.g.,
  masking, encryption of sensitive fields in transfers/exports).

## Data Quality & Reconciliation
- Late-arriving or duplicate data handling SHOULD be described.
- Reconciliation jobs SHOULD have a defined frequency and ownership.

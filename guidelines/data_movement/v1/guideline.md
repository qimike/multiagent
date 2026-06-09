# Data Movement Governance Guideline

Evaluate how data moves through the architecture — from source systems, through the data
flow and transformation stages, into target systems, and through its retention and archival
lifecycle — against these requirements.

## Source & Target Systems
- The data source system(s) and target system(s) MUST be explicitly named (e.g. the
  system of record and the analytical/archival destination).
- The boundary where data leaves the source and lands in each target MUST be clear.

## Data Flow
- The end-to-end data flow MUST be described as an ordered set of stages, clear enough to
  be reproducible (e.g. extract → stage → transform → load).
- Each movement mechanism (pipeline, batch, streaming/event, gateway) MUST be identified.
- Batch vs. streaming boundaries MUST be explicit where both exist.

## Transformation
- Where data is transformed, the transformation step and the platform performing it MUST
  be stated.
- Raw vs. transformed/derived data MUST be distinguishable.

## Lineage
- End-to-end lineage from source to consumption MUST be described or captured by tooling
  (e.g. audit/metadata capture at each stage). Partial lineage SHOULD be flagged as a gap.

## Retention
- A retention period MUST be defined for both raw and derived/historical data, including
  any regulatory retention requirement that applies.

## Archival Process
- The archival process — what is archived, where it lands, and how the source is purged or
  reclaimed after archival — MUST be specified.
- Deletion/purge behavior at the source MUST be explicit and consistent with retention.

## Data Quality & Reconciliation
- Late-arriving or duplicate data handling SHOULD be described.
- Reconciliation between source and target SHOULD have a defined frequency and ownership.

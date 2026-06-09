# Data Movement Examples

These illustrate how to map SAD text to the guideline and phrase evidence/findings. They
are illustrative — do not assume any specific section numbering.

## Example A — clear source, target, and ordered flow (conformant)
SAD text: "Extract case records from Dataverse … Persist raw data into ADLS Gen2 …
Transform data in Databricks … Load into Snowflake."
- evidence: the ordered extract → stage → transform → load steps →
  guideline "Source & Target Systems" + "Data Flow" + "Transformation" → conformant.

## Example B — archival with source purge (conformant, but check retention)
SAD text: "Purge archived records from Dataverse."
- evidence: "Purge archived records from Dataverse" → guideline "Archival Process".
- finding: archival and source purge are defined; confirm the purge is gated on a stated
  retention period (e.g. YE+7 / 10-year) so deletion is consistent with retention.

## Example C — lineage present but retention under-specified (partial)
SAD text: "Record audit metadata." with retention stated only as a business goal.
- evidence: "Record audit metadata" → "Lineage" → audit/metadata capture present.
- finding: issue "Retention period not defined for both raw (ADLS) and derived (Snowflake)
  data within the data-movement design", severity MEDIUM, recommendation "Document
  retention and archival for raw and derived data, tied to the regulatory requirement."

# Security Examples

These illustrate how to map SAD text to the guideline and phrase evidence/findings. They
are illustrative — do not assume any specific section numbering.

## Example A — approved authentication and service principals (conformant)
SAD text: "Azure AD OAuth2 … Service Principal Authentication."
- evidence: "Azure AD OAuth2" → "Authentication"; "Service Principal Authentication" →
  "Service Principals" → conformant.

## Example B — RBAC enforced across both systems (conformant)
SAD text: "Azure RBAC … Snowflake RBAC … Read Only Access."
- evidence: "Azure RBAC" + "Snowflake RBAC" → "Authorization & RBAC" enforced across the
  cloud platform and the warehouse; "Read Only Access" → read-only consumers constrained.

## Example C — encryption and network controls (conformant)
SAD text: "TLS 1.2+ … Snowflake Triple Key Encryption … Private Endpoints … Service
Endpoints."
- evidence: "TLS 1.2+" → encryption in transit; "Snowflake Triple Key Encryption" →
  encryption at rest; "Private Endpoints" → "Network Controls & Private Endpoints" →
  conformant.

## Example D — under-specified control (partial)
SAD text: encryption at rest stated for the warehouse but not for the staging layer.
- finding: issue "Encryption at rest not confirmed for the ADLS staging layer", severity
  MEDIUM, recommendation "Confirm and document encryption at rest for every store that
  holds data, including staging."

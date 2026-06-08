# Security Examples

These illustrate how to map SAD text to the guideline and phrase evidence/findings.

## Example A — compliant authentication
SAD text: "All API access requires OAuth2 via the corporate IdP."
- evidence: "All API access requires OAuth2 via the corporate IdP." → guideline
  "Approved authentication on external APIs" → conformant.

## Example B — partial: encryption in transit but not at rest
SAD text: "Traffic is encrypted with TLS 1.3. Database storage uses default settings."
- evidence: "TLS 1.3" → "Encryption in transit" → conformant.
- finding: issue "Encryption at rest is not addressed", severity HIGH,
  recommendation "Confirm and document encryption at rest for the data store."

## Example C — secrets in config files (violation)
SAD text: "Credentials are kept in application config files, rotated manually."
- finding: issue "Secrets stored in config files, not an approved vault",
  severity HIGH, recommendation "Move credentials to an approved secrets vault with
  automated rotation."

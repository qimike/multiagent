# Security Few-Shot Examples

These illustrate how to map document text to guidelines and how to phrase
evidence, violations, and assessments. Keep assessments terse and factual.

## Example A — clearly compliant authentication
Section text: "All API access requires OAuth2 via the corporate IdP."
- evidence: source_text "All API access requires OAuth2 via the corporate IdP."
  → guideline "Approved authentication on external APIs" → assessment "Compliant".

## Example B — partial: encryption in transit but not at rest
Section text: "Traffic is encrypted with TLS 1.3. Database storage uses default settings."
- evidence: TLS 1.3 → "Encryption in transit" → "Compliant".
- violation: "Sensitive data must be encrypted at rest" → reason "Encryption at
  rest is not addressed; default storage settings are not confirmed to encrypt data."
- recommendation: "Confirm and document encryption at rest for the data store."

## Example C — secrets in config files (violation)
Section text: "Credentials are kept in application config files, rotated manually."
- violation: "Secrets must be stored in an approved vault and not in config files"
  → reason "Credentials are stored in configuration files, not a vault."
- recommendation: "Move credentials to an approved secrets vault with automated rotation."

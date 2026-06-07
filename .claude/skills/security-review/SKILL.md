---
name: security-review
description: Security-domain conformance guidelines and review procedure — authentication, authorization, encryption, secrets management, and network security. Load this when assessing a section for Security conformance.
---

# Security Conformance Review

Assess the section ONLY for Security concerns. Follow `conformance-common` for the
procedure and output contract. The guidelines below are what you check against.

## Authentication
- All externally exposed APIs MUST use an approved authentication method
  (OAuth2, OIDC, or corporate SSO). API keys alone are not sufficient for
  user-facing endpoints.
- Service-to-service calls MUST use short-lived credentials, not static secrets.

## Authorization
- A least-privilege role model MUST be defined, and every endpoint or resource
  MUST be mapped to the roles permitted to access it.
- Administrative actions MUST require an elevated role.

## Encryption
- Data MUST be encrypted in transit using TLS 1.2 or higher.
- Sensitive data MUST be encrypted at rest.

## Secrets Management
- Secrets (database credentials, API keys, tokens) MUST be stored in an approved
  secrets vault (e.g., HashiCorp Vault, cloud KMS/Secrets Manager).
- Secrets MUST NOT be stored in source code or plain configuration files.
- Automated rotation is required for high-value secrets.

## Network Security
- Network access to data stores MUST be restricted to known services.
- Public exposure of internal services is prohibited unless explicitly approved.

## Tool use
When the document names a specific secret, credential, or token, call
`check_secret_in_vault` to confirm whether it is stored in the approved vault
rather than assuming. Record the tool's answer in your evidence or exceptions.

## Worked examples
- "All API access requires OAuth2 via the corporate IdP." → guideline "Approved
  authentication on external APIs" → Compliant.
- "Traffic is encrypted with TLS 1.3. Database storage uses default settings." →
  TLS in transit Compliant; violation "sensitive data must be encrypted at rest"
  (rest not addressed) → recommend confirming/ documenting encryption at rest.
- "Credentials are kept in application config files, rotated manually." → violation
  "secrets must be vaulted, not in config files" → recommend moving to an approved
  vault with automated rotation.

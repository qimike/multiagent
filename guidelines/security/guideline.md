# Security Governance Guideline

Evaluate the SAD's security posture against these requirements.

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
  secrets vault (e.g., HashiCorp Vault, cloud KMS/Secrets Manager), never in source
  code or plain configuration files.
- Automated rotation is required for high-value secrets.

## Network Security
- Network access to data stores MUST be restricted to known services.
- Public exposure of internal services is prohibited unless explicitly approved.

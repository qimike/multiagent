# Security Governance Guideline

Evaluate the SAD's security posture across authentication, authorization, encryption, and
network controls against these requirements.

## Authentication
- All externally exposed services and user-facing access MUST use an approved
  authentication method (OAuth2, OIDC, or corporate SSO / identity provider).
- API keys or static secrets alone are NOT sufficient for user-facing endpoints.

## Service Principals
- Service-to-service and pipeline authentication MUST use managed identities or service
  principals, NOT shared user accounts.
- Service principal credentials MUST be short-lived or managed; static long-lived secrets
  SHOULD be avoided.

## Authorization & RBAC
- A least-privilege role model (RBAC) MUST be defined, and access to each system/resource
  MUST be mapped to the roles permitted to use it.
- RBAC MUST be enforced consistently across every system in the flow (e.g. both the cloud
  platform and the data warehouse).
- Read-only consumers MUST be constrained to read-only roles; administrative actions MUST
  require an elevated role.

## Encryption
- Data in transit MUST be encrypted using TLS 1.2 or higher.
- Data at rest MUST be encrypted in every store that holds it (staging and warehouse).

## Network Controls & Private Endpoints
- Network access to data stores MUST be restricted to known services.
- Private endpoints / service endpoints SHOULD be used so traffic does not traverse the
  public internet; public exposure of internal services is prohibited unless explicitly
  approved.

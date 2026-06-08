# Customer 360 Platform — Solution Architecture Document

## Overview
The Customer 360 Platform consolidates customer records from CRM, billing, and
support systems into a single profile store. It exposes a REST API for internal
applications and a nightly export for the analytics team. The goal is a single
source of truth for customer data across the organization.

## Business Context
The platform supports the "Unified Customer Experience" capability, sponsored by the
VP of Customer Operations. Primary consumers are the Support, Marketing, and Billing
teams. The expected benefit is faster case resolution and fewer duplicate records.

## Data Flow
Source systems publish change events to Kafka. A streaming job lands raw events in
Snowflake, where dbt models transform them into the unified customer profile. A
separate nightly batch job reconciles records that arrive late. The platform stores
email, phone, and address fields, and a nightly export sends selected profile fields
to the analytics team. Data classification has been discussed but is not yet
documented, and there is no defined retention period for raw events or historical
profiles. Data lineage is partially captured through dbt's built-in documentation.

## Security
All external API calls authenticate via OAuth2 using the corporate identity provider
(SSO). Service-to-service traffic uses short-lived bearer tokens. Traffic between
clients and the API gateway is encrypted using TLS 1.2. Role definitions exist for
"reader" and "admin", though the mapping of roles to specific endpoints has not yet
been finalized. Database credentials are currently stored in application configuration
files and rotated manually each quarter.

## Integration
Internal applications call the REST API synchronously. The analytics team consumes the
nightly export as files on a shared bucket. Upstream CRM, billing, and support systems
integrate via their existing Kafka topics. There is no documented contract or schema
versioning strategy for the REST API or the export.

## Resilience
The service runs on the shared Kubernetes cluster with autoscaling enabled. On-call
rotation is handled by the platform team. There is no documented SLA or incident
runbook for the new API yet, and backups and recovery objectives (RTO/RPO) for the
profile store are not described.

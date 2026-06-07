# Customer 360 Platform — Solution Design

## [Data] Overview
The Customer 360 Platform consolidates customer records from CRM, billing, and
support systems into a single profile store. It exposes a REST API for internal
applications and a nightly export for the analytics team. The goal is a single
source of truth for customer data across the organization.

## [Security] Authentication & Access
All external API calls authenticate via OAuth2 using the corporate identity
provider (SSO). Service-to-service traffic uses short-lived bearer tokens.
Traffic between clients and the API gateway is encrypted using TLS 1.2.
Role definitions exist for "reader" and "admin", though the mapping of roles to
specific endpoints has not yet been finalized. Database credentials are currently
stored in application configuration files and rotated manually each quarter.

## [Data] Data Platform & Pipelines
Source systems publish change events to Kafka. A streaming job lands raw events
in Snowflake, where dbt models transform them into the unified customer profile.
A separate nightly batch job reconciles records that arrive late. The platform
stores email, phone, and address fields. Data classification has been discussed
but is not yet documented, and there is no defined retention period for raw events
or historical profiles. Data lineage is partially captured through dbt's built-in
documentation.

## [Resilient] Operations
The service runs on the shared Kubernetes cluster with autoscaling enabled.
On-call rotation is handled by the platform team. There is no documented SLA or
incident runbook for the new API yet.

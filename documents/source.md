# ISG Solution Architecture Description

**OpsTech Dynamics – Snowflake Integration**

| Field             | Value                               |
| ----------------- | ----------------------------------- |
| Business Function | Case Management (Dynamics Platform) |


---

# 1. Executive Summary

## 1.1 Overview

The Dynamics 365 Customer Engagement platform is used by Operations Technology to manage case-based workflows across enterprise operations.

The platform currently supports over 220 mailboxes, approximately 2,000 users, and several terabytes of operational data.

This SAD describes the integration of Dynamics 365 with Snowflake as an archival and reporting destination using Azure Data Factory and MS Bullet pipelines.

---

## 1.2 Business Goals

- Support continued growth of mailboxes and operational data.
- Meet DLM retention requirements.
- Enable downstream reporting and analytics.
- Reduce Dataverse storage costs.

---

## 1.3 Cloud Business Goals

- Use Snowflake as the strategic reporting warehouse.
- Leverage ADLS Gen2 as the staging layer.
- Build a future-proof architecture.

---

## 1.4 Technology Goals

- Implement ADF and MS Bullet pipelines.
- Migrate reporting workloads to Snowflake.
- Deliver Power Apps access to archived data.
- Design for future Fabric migration.

---

# 2. Requirements

## 2.1 Business Function

### Dynamics 365 Case Management

- Email2Case
- Exception2Case
- Structured Workflow
- Inbox Enhancement Platform

---

## 2.2 Business Functional Requirements

- Support mailbox growth from 220 to 500+.
- Meet YE+7 and 10-year retention requirements.
- Support analytical reporting without impacting production.

---

## 2.3 Architecturally Significant Constraints

- Data movement must be automated.
- Pipeline must be scalable.
- Future Microsoft Fabric adoption must be supported.
- Existing RBAC controls must be preserved.

---

## 2.4 Cross Functional Requirements

### Availability

- Platform Uptime: 99.9%

### Reliability

- RTO: 30 minutes
- RPO: Zero data loss
- MTTR: 2–3 hours

### Performance

- Snowflake query latency <100ms
- Weekly archival throughput >100GB

### Security

- Azure AD OAuth2
- Service Principal Authentication
- TLS 1.2+
- RBAC Enforcement

### Data Protection

- PII and MNPI supported
- Retention policies enforced

---

# 3. Current State Architecture

## 3.1 Existing Integration Patterns

Current Dynamics platform supports:

1. Email Integration
2. Reachback Notifications
3. Batch Data Feeds
4. REST APIs
5. Event Messaging
6. UI Integrations
7. Power BI Reporting

### Current State Pain Points

- Power BI queries impact production.
- Dataverse storage growth is increasing.
- No systematic archival process exists.

---

# 4. Target State Architecture

## 4.1 Logical View

Dynamics 365

↓

ADF Pipeline

↓

ADLS Gen2

↓

Databricks

↓

Snowflake

↓

Power BI / Power Apps

---

## 4.2 Archival Data Flow

### Step 1

Retrieve archival configuration.

### Step 2

Extract case records from Dataverse.

### Step 3

Persist raw data into ADLS Gen2.

### Step 4

Record audit metadata.

### Step 5

Transform data in Databricks.

### Step 6

Load into Snowflake.

### Step 7

Purge archived records from Dataverse.

---

## 4.3 Resiliency Design

| Layer     | Mechanism                |
| --------- | ------------------------ |
| Dynamics  | Native HA                |
| ADF       | Automatic Retry          |
| Azure SQL | Geo Replication          |
| Snowflake | Cross Region Replication |
| ADLS      | ZRS / GRS                |

---

## 4.4 Security View – Dataverse to Snowflake

### Authentication

- Azure AD OAuth2
- Service Principal Authentication

### Authorization

- Azure RBAC
- Snowflake RBAC

### Encryption

- TLS 1.2+
- Snowflake Triple Key Encryption

### Network

- Private Endpoints
- Service Endpoints

---

## 4.5 Security View – Power Apps Access

### User Access

Operations User

↓

Power Apps

↓

Power Platform Gateway

↓

Snowflake

### Controls

- Azure AD Authentication
- RBAC Enforcement
- Read Only Access

---

# 6. Related ADRs
None


---

# 7. Related Cloud Pipelines
None

---

# 8. Additional Information

## 8.1 Lessons Learned

Not recorded at document creation.

## 8.2 Assessments Conducted

Not recorded at document creation.

---

# 9. Alignment with ISG Architecture Principles

## Security

Azure AD, RBAC, TLS, Encryption.

## Data

Retention, Classification, Governance.

## Reliability

RTO, RPO, Replication.

## Simplicity

Reuse strategic platforms.

## Modernization

Cloud-native architecture.

---

# 10. Risk Profile

## Asset Risk Level

P1

## Risk Log

No active risks recorded.

---

# Appendix

## A1 Key Architecture Decisions

### Long Term Retention

Selected:
ADF + Snowflake Pipeline

Reason:
Improved reporting and retention capability.

---

### Data Warehouse Platform

Selected:
Snowflake

Reason:
Strategic enterprise platform.

---

### Pipeline Design

Selected:
Dynamics → ADF → MS Bullet → Snowflake

Reason:
Performance, reuse, operational simplicity.

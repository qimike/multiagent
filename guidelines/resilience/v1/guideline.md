# Resilience Governance Guideline

Evaluate the SAD's ability to stay available and recover from failure — across recovery
objectives, retry/failover behavior, replication, and disaster recovery — against these
requirements.

## Availability
- An availability target (SLA/SLO) MUST be stated for the service and its critical
  externally consumed dependencies.

## Recovery Objectives (RTO / RPO)
- Recovery objectives MUST be stated for critical data and services:
  - RTO (how quickly service must be restored) MUST be defined.
  - RPO (maximum tolerable data loss) MUST be defined.
- Where zero data loss is claimed, the mechanism that achieves it MUST be identified.

## Retry Strategy
- Transient-failure handling (retries, timeouts, backoff) SHOULD be described for each
  movement/integration stage that can fail.

## Failover
- Single points of failure MUST be identified and addressed.
- Failover behavior MUST be described for critical components.

## Replication
- Replication of critical data stores (e.g. geo/cross-region or zone-redundant) MUST be
  described where it underpins the recovery objectives.

## Disaster Recovery
- A disaster-recovery approach MUST be defined, and restore MUST be testable.
- The DR approach MUST be consistent with the stated RTO/RPO.

## Monitoring & Graceful Degradation
- Health checks, key metrics, and alerting coverage SHOULD be described for the service and
  its critical dependencies.
- Behavior under partial failure or overload (graceful degradation, backpressure) SHOULD be
  described.

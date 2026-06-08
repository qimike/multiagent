# Resilience Governance Guideline

Evaluate the SAD's ability to stay available and recover from failure against these
requirements.

## Availability Targets (SLA/SLO)
- Availability and latency targets (SLA/SLO) MUST be stated for each externally
  consumed service, with an owner.

## Redundancy & Failover
- Single points of failure MUST be identified and addressed (e.g., multi-AZ or
  multi-region, redundant instances).
- Failover behavior MUST be described for critical components.

## Disaster Recovery
- Backups MUST be defined, and restore MUST be testable.
- Recovery objectives (RTO/RPO) MUST be stated for critical data and services.

## Incident Response
- On-call ownership, escalation paths, and an incident runbook SHOULD be documented.

## Monitoring & Alerting
- Health checks, key metrics, and alerting coverage MUST be described for the
  service and its critical dependencies.

## Scalability & Graceful Degradation
- Autoscaling or capacity limits SHOULD be described.
- Behavior under partial failure or overload (graceful degradation, backpressure,
  retries/timeouts) SHOULD be described.

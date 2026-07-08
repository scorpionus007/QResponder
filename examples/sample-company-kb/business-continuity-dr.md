Tags: policy, business-continuity, disaster-recovery, availability, soc2

# Business Continuity & Disaster Recovery

**Owner:** Engineering & Security · **Review cadence:** annually; DR tested annually.

## Objectives

- **Recovery Point Objective (RPO): 1 hour** — the maximum acceptable data loss.
- **Recovery Time Objective (RTO): 4 hours** — the target time to restore service.
- **Availability target:** 99.9% monthly uptime for the production platform.

## Resilience architecture

The platform is deployed across **multiple AWS Availability Zones** within a region.
Databases (Amazon RDS) run in Multi-AZ mode with automated failover. Stateless
application services run behind load balancers with health-checked auto-scaling, so
the loss of a single instance or AZ does not cause an outage.

## Backups

Databases are backed up continuously (point-in-time recovery) with daily snapshots
retained for 30 days. Backups are encrypted (AES-256, KMS) and stored in a separate
AWS region for regional resilience. Restore procedures are documented and tested (see
Backup Policy).

## DR testing

Disaster recovery is tested **at least annually**, including database restore drills
and failover exercises. Test results and RTO/RPO measurements are documented, and any
gaps are remediated.

## Business continuity

A business continuity plan covers key personnel, communications, and vendor
dependencies. Critical staff have documented backups, and the plan is reviewed
annually. In the event of a major disruption, the Incident Response Plan governs
coordination and customer communication.

Tags: policy, backup, availability, disaster-recovery, soc2

# Backup Policy

**Owner:** Engineering · **Review cadence:** annually; restores tested at least
annually.

## What is backed up

- **Relational data (Amazon RDS/PostgreSQL):** continuous backups with point-in-time
  recovery, plus automated daily snapshots.
- **Object storage (Amazon S3):** versioning enabled; critical buckets replicated to a
  second region.
- **Configuration/infrastructure:** defined as code in version control, so
  environments are reproducible.

## Retention and location

- Snapshots and backups are **retained for 30 days** on a rolling basis.
- Backups are **encrypted with AES-256** using KMS-managed keys.
- A copy of backups is stored in a **separate AWS region** for regional resilience.

## Recovery objectives

- **RPO: 1 hour** (maximum data loss).
- **RTO: 4 hours** (target restore time).

## Restore testing

Restore procedures are documented in runbooks and **tested at least annually**,
including full database restore drills. Test outcomes (including measured RPO/RTO) are
recorded and any gaps remediated.

## Access

Access to backups and snapshots is restricted via IAM to authorized engineers and is
logged. Backups inherit the same encryption and access controls as production data.

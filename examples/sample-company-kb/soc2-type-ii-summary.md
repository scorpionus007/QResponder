Tags: soc2, compliance, audit

# SOC 2 Type II Report Summary

Sample Inc. undergoes an annual **SOC 2 Type II** examination performed by an
independent, licensed CPA firm.

## Scope

- **Trust Services Criteria in scope:** Security (Common Criteria), Availability, and
  Confidentiality. Processing Integrity and Privacy are not currently in scope.
- **System:** the Sample Inc. SaaS platform and the supporting AWS infrastructure,
  including production application services, databases, and the CI/CD pipeline.
- **Observation period:** a continuous 12-month period; the report is a Type II
  (operating effectiveness over time), not a point-in-time Type I.

## Result

The most recent report was issued with an **unqualified (clean) opinion and no
exceptions noted**. Controls tested include logical access, change management,
encryption, network security, monitoring and alerting, incident response, backup and
recovery, and vendor management.

## Availability commitments

Sample Inc. targets **99.9% monthly uptime** for the production platform, backed by
multi-AZ deployment, health-checked auto-scaling, and documented recovery objectives
(RPO 1 hour, RTO 4 hours — see Business Continuity & Disaster Recovery).

## Obtaining the report

The full SOC 2 Type II report and the auditor's bridge letter are available to
customers and prospects **under a mutual NDA**. Requests are handled by the Security
team via security@sample.example, typically within two business days.

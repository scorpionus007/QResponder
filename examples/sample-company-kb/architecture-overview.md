Tags: architecture, infrastructure, security, network

# Platform Architecture Overview

**Owner:** Engineering · **Review cadence:** on significant change.

## High level

The Sample Inc. platform is a multi-tenant SaaS application hosted on **AWS**. It
follows a standard three-tier design: a web/API tier, an application-services tier,
and a data tier, all deployed across multiple Availability Zones.

## Network and boundaries

- Public traffic terminates at an **Application Load Balancer** with a **WAF** in front
  for common web attack protection (OWASP Top 10 rulesets) and rate limiting.
- Application and database components run in **private subnets** with no direct inbound
  internet access. Egress is controlled through NAT gateways.
- **Security groups** and network ACLs enforce least-privilege connectivity between
  tiers; only required ports are open.
- Administrative access to infrastructure is via SSO + MFA through a bastion/SSM;
  there are no shared SSH keys.

## Data tier

- **Amazon RDS for PostgreSQL** (Multi-AZ, encrypted with KMS) for relational data.
- **Amazon S3** (SSE-KMS) for object storage.
- Tenant isolation is enforced at the application layer with per-tenant scoping on
  every query; a tenant identifier is required and validated on all data access.

## Tenancy and isolation

The platform is **logically multi-tenant**: customer data is isolated by tenant
context enforced in application code and tested. Dedicated single-tenant deployments
are available on Enterprise plans.

## CI/CD

Code ships through an automated CI/CD pipeline with mandatory peer review, automated
tests, dependency and container scanning, and infrastructure-as-code. Production
deploys are gated and auditable (see Secure SDLC & Change Management).

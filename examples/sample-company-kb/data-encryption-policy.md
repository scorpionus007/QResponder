Tags: policy, encryption, security, soc2

# Data Encryption Policy

**Owner:** Security Engineering · **Review cadence:** annually.

## Encryption at rest

All customer data at rest is encrypted using **AES-256**. Encryption is applied at
the storage layer:

- **Databases:** Amazon RDS for PostgreSQL with encryption enabled; keys managed by
  **AWS KMS**.
- **Object storage:** Amazon S3 with server-side encryption (SSE-KMS).
- **Backups and snapshots:** encrypted with the same KMS-managed keys.

Encryption keys are managed in AWS KMS. Key rotation is enabled (annual automatic
rotation for KMS-managed keys), and access to keys is restricted via IAM policy and
logged in CloudTrail.

## Encryption in transit

All data transmitted over public networks is encrypted using **TLS 1.2 or higher**
(TLS 1.3 preferred). This applies to:

- Customer connections to the application (HTTPS only; HTTP is redirected to HTTPS).
- API traffic and webhooks.
- Connections between internal services where they traverse network boundaries.

Weak ciphers and protocols (SSLv3, TLS 1.0/1.1) are disabled. HSTS is enabled on
customer-facing endpoints.

## Key management and secrets

Application secrets and credentials are stored in **AWS Secrets Manager**, never in
source code or configuration files. Access is scoped by IAM role and audited.
Developers do not have access to production KMS keys or customer data by default.

## Summary

- Data at rest: **AES-256** (KMS-managed).
- Data in transit: **TLS 1.2+** (1.3 preferred).
- Keys: AWS KMS with rotation; secrets in AWS Secrets Manager.

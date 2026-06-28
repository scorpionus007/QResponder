# Data Encryption Policy

Tags: soc2, encryption, security

All customer data at rest is encrypted using AES-256. Encryption keys are
managed via the cloud provider's Key Management Service (KMS) and rotated
annually. Data in transit is protected with TLS 1.2 or higher.

Database-level encryption and full-disk encryption are enabled on all
production systems.

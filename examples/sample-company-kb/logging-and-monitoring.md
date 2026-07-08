Tags: policy, logging, monitoring, security, soc2

# Logging & Monitoring

**Owner:** Security & Engineering · **Review cadence:** annually.

## Logging

- **Audit logs:** administrative and security-relevant actions (authentication,
  authorization changes, access to sensitive data, configuration changes) are logged.
- **Infrastructure logs:** AWS **CloudTrail** records API/control-plane activity; VPC
  flow logs capture network activity.
- **Application logs:** structured logs are shipped to a centralized, access-controlled
  observability platform.
- **Integrity:** logs are stored in append-only/immutable storage where practical and
  are protected from tampering; access is restricted and itself logged.
- **Retention:** logs are retained for **12 months** (see Data Retention & Disposal).

## Monitoring and alerting

- Automated alerts fire on security-relevant events (e.g., anomalous logins, IAM
  changes, disabled controls) and on availability/health signals.
- Alerts route to the on-call rotation 24/7; runbooks define response steps.
- Metrics and dashboards track service health against the 99.9% availability target.

## Detection

Sample Inc. uses cloud-native threat detection (e.g., anomaly detection on account
activity) and reviews high-signal alerts. Suspected incidents follow the Incident
Response Plan.

## Customer visibility

Customer administrators have access to an in-product **audit log** of user and admin
activity within their own tenant, which they can review and export.

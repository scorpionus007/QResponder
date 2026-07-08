Tags: policy, access-control, iam, security, soc2

# Access Control & Identity Policy

**Owner:** IT & Security · **Review cadence:** annually; access reviews quarterly.

## Identity and authentication

- **Single sign-on (SSO):** all corporate applications are accessed through **Okta**
  as the central identity provider.
- **Multi-factor authentication (MFA):** MFA is **enforced for all employees** on SSO
  and for all administrative access to production systems.
- **Password standards:** minimum 12 characters, complexity enforced, checked against
  known-breached password lists. Passwords are never reused across systems.

## Authorization

- **Role-based access control (RBAC):** access is granted based on job role following
  the principle of **least privilege**.
- **Provisioning/deprovisioning:** access is provisioned through a ticketed request
  with manager approval. On termination, access is revoked within **24 hours** (SSO
  is disabled immediately on the employee's last day).
- **Privileged access:** administrative and production access requires additional
  approval, is time-limited where possible, and is logged. Direct production database
  access is restricted to a small on-call group and is audited.

## Access reviews

Access to production systems and customer data is reviewed **at least quarterly** by
system owners; discrepancies are remediated and documented. Service accounts and API
keys are inventoried and rotated on a defined schedule.

## Customer-facing access controls

The product supports **SSO/SAML** and **SCIM** provisioning for customers, granular
role-based permissions, and session timeout controls. Customer administrators manage
their own users and roles.

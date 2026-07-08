Tags: policy, sdlc, change-management, security, soc2

# Secure Development & Change Management

**Owner:** Engineering & Security · **Review cadence:** annually.

## Secure SDLC

Sample Inc. follows a secure software development lifecycle:

- **Design:** security-relevant changes undergo threat modeling and security review.
- **Code review:** every change requires **peer review** and approval before merge; no
  direct commits to the main branch.
- **Automated checks in CI:** unit/integration tests, static analysis (SAST),
  dependency scanning, secret scanning, and container image scanning run on every pull
  request. Builds fail on new high/critical findings.
- **Developer training:** engineers receive secure-coding training covering the OWASP
  Top 10 and secure handling of secrets and customer data.

## Change management

- Changes are tracked in version control and a ticketing system with an audit trail
  (who, what, when, approval).
- Production deploys are automated through the CI/CD pipeline, gated by passing tests
  and required approvals. Deploys are logged and are **rollback-capable**.
- **Separation of duties:** the person who authors a change is not the sole approver;
  production access for deploys is controlled and audited.
- Emergency changes follow an expedited but still-reviewed and documented process, with
  retroactive review.

## Environments

Development, staging, and production are separated. **Production data is not used in
non-production environments**; test data is synthetic or anonymized. Access to
production is restricted and requires SSO + MFA.

## Infrastructure as code

Infrastructure is defined as code and peer-reviewed, so environment changes are
version-controlled, repeatable, and auditable.

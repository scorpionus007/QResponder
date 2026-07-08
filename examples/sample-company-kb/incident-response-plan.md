Tags: policy, incident-response, security, soc2

# Incident Response Plan

**Owner:** Security team · **Review cadence:** annually; tested at least annually.

Sample Inc. maintains a documented incident response plan with defined severity
levels, on-call roles, and post-incident review.

## Roles

- **Incident Commander (IC):** owns coordination and decisions during an incident.
- **On-call engineer:** first responder; triages and mitigates.
- **Security lead:** assesses scope, data impact, and containment.
- **Communications lead:** manages internal and customer communications.

## Severity levels

- **SEV-1:** confirmed breach of customer data or full production outage. All-hands.
- **SEV-2:** significant security or availability impact; partial outage.
- **SEV-3:** limited impact; workaround available.

## Process

1. **Detect** — via monitoring/alerting, customer report, or employee report to
   security@sample.example.
2. **Triage & declare** — assign severity and an Incident Commander.
3. **Contain** — isolate affected systems, revoke credentials, block malicious access.
4. **Eradicate & recover** — remove the root cause and restore service from known-good
   state (see Backup Policy).
5. **Notify** — for confirmed breaches of customer data, Sample Inc. notifies affected
   customers **without undue delay and within 72 hours** of confirmation, consistent
   with contractual and regulatory obligations.
6. **Post-incident review** — a blameless RCA is completed within 5 business days with
   tracked corrective actions.

## Testing

The plan is exercised at least annually through a tabletop or simulation, and lessons
learned feed back into controls and runbooks.

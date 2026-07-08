# Sample Inc. — demo knowledge base

A **fictional** company's security/compliance documentation, for trying QRESPONDER
end-to-end. Everything here is invented for demo purposes — Sample Inc. is not a real
company and these are not real policies.

Use it as a workspace knowledge base: the docs are the sources QRESPONDER retrieves
from, cites, and grounds answers in when you Ask a question or Upload a questionnaire.

## What's in here

| Document | Covers |
| --- | --- |
| `00-company-security-overview.md` | Company + security program summary, certifications |
| `information-security-policy.md` | Governance, least privilege, data classification |
| `soc2-type-ii-summary.md` | SOC 2 Type II scope, result, how to request the report |
| `data-encryption-policy.md` | AES-256 at rest, TLS 1.2+ in transit, KMS keys |
| `access-control-policy.md` | SSO/Okta, MFA, RBAC, quarterly access reviews |
| `incident-response-plan.md` | Severity levels, roles, 72-hour breach notification |
| `business-continuity-dr.md` | RPO 1h / RTO 4h, multi-AZ, DR testing |
| `data-retention-and-disposal.md` | Retention windows, deletion within 30 days |
| `vendor-risk-management.md` | Subprocessors, DPAs, PCI, ongoing monitoring |
| `architecture-overview.md` | AWS multi-AZ, WAF, tenancy/isolation, CI/CD |
| `vulnerability-management.md` | Weekly scanning, remediation SLAs, annual pentest |
| `secure-sdlc-change-management.md` | Peer review, SAST, separation of duties |
| `hr-security-and-training.md` | Background checks, annual training, offboarding |
| `privacy-and-data-processing.md` | Processor role, DPA/SCCs, GDPR/CCPA, no AI training |
| `backup-policy.md` | Encrypted backups, 30-day retention, restore testing |
| `logging-and-monitoring.md` | Audit logs, 12-month retention, 24/7 alerting |

There's also a `sample-questionnaire.xlsx` you can run through **Upload**.

## Try it (2 minutes)

**Web UI** — create a workspace, then on **Home** or **Knowledge Base → Documents &
sources** drop in these files (or use **Connections → Folder** pointed at this
directory). Then go to **Ask** and try:

- "Do you encrypt data at rest and in transit?"
- "What is your RTO and RPO?"
- "How often do you run penetration tests?"
- "How long do you retain customer data after termination?"
- "Do you have MFA and SSO?"

**CLI**

```bash
qresponder ask "Do you encrypt data at rest?" --kb examples/sample-company-kb
qresponder answer -q examples/sample-company-kb/sample-questionnaire.xlsx \
  --kb examples/sample-company-kb --out ./out
```

Every answer is grounded in and cited from these docs — and QRESPONDER abstains
(flags for review) when the KB doesn't cover a question, instead of guessing.

> **Tip:** with this many docs, switch the workspace to **retrieval mode**
> (Settings → Engine settings → Retrieval mode = `retrieval`, or `KB_MODE=retrieval`)
> so well-supported answers reach HIGH confidence and auto-answer. In-context mode
> stays more conservative. The `sample-questionnaire.xlsx` includes one deliberately
> unanswerable question (a "2027 quantum-resistant roadmap") so you can see QRESPONDER
> flag it for review instead of fabricating.

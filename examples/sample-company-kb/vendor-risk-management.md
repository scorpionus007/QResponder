Tags: policy, vendor-risk, third-party, security, soc2

# Third-Party / Vendor Risk Management

**Owner:** Security & Procurement · **Review cadence:** annually; vendors reviewed on
onboarding and yearly.

## Program

Before a vendor or subprocessor can handle Sample Inc. or customer data, it goes
through a security review proportional to its risk. The review considers the
vendor's SOC 2 / ISO 27001 status, data handling, encryption, access controls, and
breach-notification commitments. A signed Data Processing Agreement (DPA) is required
for any vendor processing personal data.

## Subprocessors

Sample Inc. uses a limited set of vetted subprocessors, including:

- **Amazon Web Services (AWS)** — cloud infrastructure hosting.
- **A managed email/notification provider** — transactional email.
- **A payment processor** — billing (PCI-DSS compliant; Sample Inc. does not store
  full card numbers).
- **A support/ticketing platform** and an **observability provider** for logs/metrics.

A current list of subprocessors is maintained and available to customers; material
changes are communicated with advance notice per the DPA.

## Ongoing monitoring

Vendors are reassessed at least annually and when their scope or risk changes.
Critical vendors are monitored for security incidents and certification lapses.
Access granted to vendors follows least privilege and is removed when no longer
needed.

## PCI and payments

Payment card data is handled entirely by a PCI-DSS Level 1 payment processor;
Sample Inc.'s systems do not store, process, or transmit full primary account
numbers.

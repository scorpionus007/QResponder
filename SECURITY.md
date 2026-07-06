# Security Policy

QRESPONDER is a **local-first** tool: by default it binds `127.0.0.1`, has no
authentication, sends no telemetry, and — with a local model — makes zero external
calls. Most of its security posture is therefore in your hands (where you run it and
whether you expose it). This document covers reporting issues in the software itself.

## Supported versions

We support the **latest released version** on `main`. Fixes land there first and are
included in the next tagged release.

| Version        | Supported |
| -------------- | --------- |
| latest release | ✅        |
| older releases | ❌        |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately via **GitHub Security Advisories**: open the repository's
**Security → Report a vulnerability** page (GitHub → *Report a vulnerability*). If
that is unavailable to you, open a minimal public issue asking a maintainer to open a
private channel — without any exploit details.

Please include:

- A description of the issue and its impact.
- Steps to reproduce (a minimal proof-of-concept is ideal).
- The version/commit and how you were running it (local, Docker, hosted).

We aim to acknowledge reports within a few days and to ship a fix or mitigation as
quickly as the severity warrants. We'll credit you in the release notes unless you
prefer to remain anonymous.

## Scope notes

- **Credential handling.** Provider API keys and connector OAuth secrets/tokens are
  stored server-side and are never returned to the browser, echoed after entry, or
  logged. A leak of a secret into any HTTP response, log line, or event stream is
  in scope.
- **Grounding guarantees.** A path that lets a generated answer bypass
  `snippet_supported` + faithfulness (i.e. an ungrounded answer served as grounded)
  is a correctness/security concern — please report it.
- **Hosting.** Running a no-auth instance on a network is a *configuration* choice we
  loudly warn against (see [docs/hosting.md](docs/hosting.md)); the exposure of an
  intentionally-public no-auth instance is not itself a vulnerability in the tool.

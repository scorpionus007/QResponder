# Security & privacy

QRESPONDER is built to keep your data on your machine. This page states exactly what
stays local and what changes if you opt into a cloud model or expose the app.

## Local by default

- **Binds `127.0.0.1`** and has **no authentication** — it's a single-user local tool.
- **No telemetry.** The app never phones home; there is no analytics or usage
  reporting of any kind.
- **Zero external calls when fully local.** With a local model (Ollama/vLLM/LM Studio)
  and local embeddings/reranker, the *answering* path makes no network requests at all.
- **The UI loads zero external assets** — no CDN, no web fonts, no third-party scripts.

## Credentials

- A **cloud provider API key** (if you use one) lives in `.env` on the server. It is
  used server-side only and is **never sent to the browser** or included in any API
  response.
- **Connector OAuth secrets and access/refresh tokens** are stored server-side (a
  connection's secret store), never returned to the browser, never echoed after entry,
  and never written to logs. The Connections list shows *status only*.

## What a cloud model changes

If you set `LLM_PROVIDER` to a cloud provider (Anthropic/OpenAI/Gemini/DeepSeek), the
*answering* path sends your prompt (question + retrieved KB context) to that provider,
subject to their terms. That's inherent to using a hosted model. Everything else
(storage, connectors, the UI) stays local. Prefer a local model if the KB content must
never leave the host.

## Connectors

Connectors fetch from third-party services **only** when you explicitly Test or Sync a
connection — **never during answering**. Each fetch is bounded/paginated with
timeouts; URL inputs are SSRF-guarded.

## Exposing it on a network (opt-in)

The default is local-only. If you deliberately expose it, set `QRESPONDER_AUTH_TOKEN`
and put a reverse proxy with TLS in front — see [hosting.md](hosting.md). A no-auth
instance on a network exposes your entire knowledge base; the app prints a loud warning
if you bind beyond loopback without the token set.

## Reporting a vulnerability

See [SECURITY.md](../SECURITY.md) — please report privately, not in a public issue.

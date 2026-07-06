# Architecture

QRESPONDER turns a security questionnaire into grounded, cited draft answers — and
abstains when the knowledge base can't support one. It is deliberately small,
layered, and offline-testable. This document is the map.

## The one rule

There is **one** answering path, and everything routes through it:

```
Tier-1 Answer Library (exact/near reuse)
   └─ else → hybrid retrieval (BM25 + dense + RRF) → rerank
            → grounded generation (answer only from retrieved context)
            → snippet_supported check + faithfulness judge
            → confidence (rule-based HIGH/MED/LOW) or ABSTAIN (NEEDS_REVIEW)
```

No path skips grounding. A generated answer that isn't supported by a cited snippet
becomes `NEEDS_REVIEW`, never a confident guess. Tier-1 (human-approved) answers are
exempt from the judge and never overridden.

## Layers

```
ingest → extract → orchestrate → output
```

- **ingest** (`ingestion/`, `core/bulk_ingest.py`): xlsx/docx/pdf/csv/… → a
  layout-aware intermediate representation; bulk any-format ingestion into the KB.
- **extract**: pull the questions out of a questionnaire (LLM call #1).
- **orchestrate** (`core/orchestrate.py`): the rule above — library match →
  ambiguity/decomposition → retrieval/in-context → grounded generation (LLM call #2)
  → faithfulness → confidence → conflict/injection checks → answer-type shaping.
- **output** (`output/`): `answered.*` + `results.json` + `review.md`, and
  format-preserving write-back into a copy of the original file (never overwriting it).

## Key modules

| Area | Module(s) | Notes |
| --- | --- | --- |
| Config | `config.py` | env + `.env`; keys/secrets are server-side only |
| Models | `models.py` | pydantic v2, **additive-only** |
| Providers | `llm/providers.py`, `llm/models.py` | multi-provider routing; live key-gated model lists; **no silent mock fallback** |
| Retrieval | `kb/retrieval.py`, `kb/in_context.py`, `llm/embeddings.py`, `llm/reranker.py` | retrieval deps are the `retrieval` extra, lazy-imported |
| Library | `kb/library.py`, `core/flywheel.py` | Tier-1 reuse + the approve-to-train flywheel |
| Faithfulness | `core/faithfulness.py`, `core/confidence.py` | the grounding gate |
| Workspaces | `core/workspace.py` | isolated `kb/`, `evidence/`, `qa.yaml`, `runs/`, `connections.json` |
| Connectors | `connectors/` | pluggable sources; injectable HTTP so tests are offline; see below |
| Connections | `core/connections.py` | non-secret connection records + a separate server-side secret store |
| Analytics | `core/stats.py`, `core/insights.py` | local read-only reports (usage + knowledge gaps) |
| Web | `web/app.py`, `web/static/` | thin FastAPI + vanilla JS; **no answering logic here** |

## Connectors

Each connector implements `Connector.fetch() -> [SourceDoc]` plus
`test_connection()`; ingestion always reuses the bulk path (validation, sandbox,
provenance sidecar, tags) — connectors never reimplement it.

- **Local**: folder (path-contained), website (bounded BFS + SSRF guard).
- **SaaS** (`TokenConnector`): Notion, Google Drive, SharePoint, OneDrive,
  Confluence — real REST APIs with cursor/pageToken/`@odata.nextLink` pagination.
  An **injectable HTTP fetcher** means the real pagination/download logic runs
  offline against real-API-shaped mocks.
- **Credentials** come from a one-time server-side OAuth app (or a token in `.env`).
  The client secret and access/refresh tokens are stored server-side and never reach
  the browser. Connectors run **only** on an explicit `connect`/test/sync — never
  during answering.

See [docs/connectors.md](docs/connectors.md).

## Boundaries (invariants)

- **Local-first**: with a local model + local embeddings/reranker, answering makes
  zero external calls. No telemetry. Binds `127.0.0.1` by default.
- **Secrets server-side**: never in a response, log, or event.
- **Thin web layer**: `web/` writes workspace files and calls the engine; it holds
  no answering logic.
- **Additive models**: `models.py` only grows; existing fields don't change meaning.
- **Offline tests**: the whole suite runs with a `MockProvider` and injected
  HTTP/embedder/reranker — no network.

## Adding a source connector

1. Subclass `TokenConnector` (SaaS) or `Connector` (local) in `connectors/`.
2. Implement `_make_client()` using `self._http` (injectable) for the real API, and
   `test_connection()` for a cheap reachability probe.
3. Register it in `core/connections.build_connector` and the `/api/connectors` list;
   if it's OAuth, add a spec to `connectors/oauth.OAUTH_SPECS` (+ config client
   id/secret) and, if it rides another provider's identity, `CONNECTOR_OAUTH`.
4. Add an **offline** test with a real-API-shaped mock (see
   `tests/test_connectors_hardening.py`).

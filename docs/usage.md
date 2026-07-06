# Usage

## The web UI

`qresponder serve` (or `docker compose up -d`) → open `http://127.0.0.1:8000`. A left
icon rail navigates:

- **Home** — first-run checklist, local-first assurance, and a hero drop-zone to add
  your first knowledge-base document.
- **Upload** — drop `.docx/.pdf/.xlsx/.csv` questionnaires; pick the model + an
  optional style preset; watch the live "AI Thinking" processing; download the filled
  originals per file.
- **Ask** — one question → a grounded, cited answer (or an honest abstention), with an
  inline **Regenerate** (style-only guidance) and **Save to library**.
- **Knowledge Base** — Entries (Q&A), Documents & sources, Flagged (cross-file
  resolve), Duplicates (`kb-check`).
- **Connections** — add/test/sync source connectors (see [connectors.md](connectors.md)).
- **Insights** — a knowledge-gap report: what your KB can't yet answer.
- **Settings** — model, engine behavior, analytics, danger zone.

Every answer is grounded and cited, or it abstains. Nothing is auto-submitted — you
review, and each accept trains the workspace's answer library.

## The CLI

```bash
qresponder doctor                                   # verify your model + config
qresponder answer -q q.xlsx --kb ./kb --qa qa.yaml --out ./out   # single file
qresponder answer -q ./inbox --batch --out ./out                  # a folder (batch)
qresponder ask "Do you encrypt data at rest?" --workspace acme    # one question
qresponder connect folder ./policies --workspace acme --tags soc2 # ingest a source
qresponder stats --workspace acme                    # completion / auto-answer analytics
qresponder kb-insights --workspace acme              # knowledge-gap report
qresponder kb-check --qa qa.yaml                     # library contradictions/dups
qresponder serve                                     # the web UI
```

Run `qresponder --help` for the full command list.

## The grounded flow (what's happening)

For each question: reuse a human-approved answer if one matches (**Tier-1**),
otherwise retrieve from your KB, generate an answer **only from that context**, verify
each claim is entailed by a cited snippet (**faithfulness**), and assign a rule-based
confidence — or **abstain** (`NEEDS_REVIEW`) when the KB doesn't support an answer.
There is no path that answers without grounding.

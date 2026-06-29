# Contributing to QRESPONDER

Thanks for your interest! QRESPONDER is a local-first, bring-your-own-model
security-questionnaire automation tool. The bar is correctness: **a confidently
wrong compliance answer is worse than no answer.**

## Dev setup

```bash
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[anthropic,openai,retrieval,dev]"
pytest                                           # all tests run offline (MockProvider)
```

The full suite is **network-free** — it uses `MockProvider` and injected stub
embedders/rerankers. New code must keep it that way.

## Non-negotiable guardrails (see the build spec §4)

- **Grounding:** answer only from supplied KB context; unsupported → `NEEDS_REVIEW`
  + `missing_info`. Never fabricate certifications, controls, audits, or status.
- **Citations:** every `ANSWERED` result carries ≥1 citation; generated answers
  are filtered by `snippet_supported` and checked for faithfulness.
- **Tier-1 is the authority:** approved Answer Library entries are exempt from the
  faithfulness judge and are never silently overridden by a generated answer.
- **Human gate:** output is a draft; there is no submit step. Write-back fills a
  **copy**, never the original, and never strips embedded media.
- **Local-first:** the fully-local path makes zero external network calls. No
  telemetry, ever. Temperature 0.0 everywhere.
- **Provider-agnostic:** depend on the `LLMProvider` protocol, never a concrete
  SDK. Instruct-strict-JSON + defensive parse is the default — don't make a
  vendor-specific structured-output mode the default.
- **Model changes are additive only** — new optional fields/models; don't break
  existing field contracts.

## Workflow

1. Open or pick an issue (see **good first issues** below).
2. Branch, implement, and **add a `MockProvider`-based test** for the behavior.
3. `pytest` green locally; CI must stay green.
4. Open a PR describing the change and which guardrails it touches.

## Good first issues

See [docs/GOOD_FIRST_ISSUES.md](docs/GOOD_FIRST_ISSUES.md).

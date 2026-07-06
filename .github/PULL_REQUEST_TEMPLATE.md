## What & why

<!-- What does this change and why? Link any issue: Closes #123 -->

## Checklist

- [ ] `pytest -q` passes (all offline — no network in tests)
- [ ] Added/updated tests for the change
- [ ] No secret is ever sent to the browser / a response / a log (if touching
      providers or connectors)
- [ ] Grounding is unchanged: answers still go through the single grounded path
      (`snippet_supported` + faithfulness + abstain); no new "answer anyway" path
- [ ] Thin web layer — no answering logic moved into `web/`
- [ ] No CDN / external fonts / telemetry added to the UI
- [ ] Docs / CHANGELOG updated if user-facing

## Notes for reviewers

<!-- Anything non-obvious; how you verified; screenshots for UI changes -->

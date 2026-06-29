#!/usr/bin/env bash
# QRESPONDER demo — produces the exact artifacts shown in the README, using the
# deterministic mock provider (offline, no API key needed). This is the run
# recorded for the demo GIF.
#
#   pip install -e ".[anthropic,openai]"   # once
#   bash scripts/demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

export LLM_PROVIDER=mock
OUT=demo_out

echo "==> Generating sample questionnaire + fixtures"
python tests/make_fixtures.py

echo "==> Running qresponder answer (in-context, with evidence + write-back)"
qresponder answer \
  --questionnaire tests/fixtures/sample.xlsx \
  --kb tests/fixtures/kb \
  --qa qa.example.yaml \
  --evidence tests/fixtures/evidence \
  --tags soc2 \
  --writeback \
  --out "$OUT"

echo
echo "==> Baseline eval against the golden set"
qresponder eval --set eval.yaml --kb tests/fixtures/kb --qa qa.example.yaml

echo
echo "Artifacts written to $OUT/:"
echo "  - answered.xlsx          (clean answers + citations + confidence + status)"
echo "  - results.json           (machine-readable; edit, then 'qresponder approve')"
echo "  - review.md              (human-first: review items first, grouped by reason)"
echo "  - sample.answered.xlsx   (your original template, filled in a copy)"

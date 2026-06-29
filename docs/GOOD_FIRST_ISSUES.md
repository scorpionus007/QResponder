# Good first issues

Scoped starter tasks. Each is self-contained, has a clear acceptance test, and
touches one area. File these as GitHub issues with the `good first issue` label.

### 1. `qresponder approve --dry-run`
Add a `--dry-run` flag to the `approve` command that prints what *would* be added
/ version-bumped without writing `qa.yaml`.
**Acceptance:** a test asserts the library file is unchanged and the summary
lists the pending changes. Area: `core/flywheel.py`, `cli.py`.

### 2. CSV questionnaire ingestion
Add a `.csv` loader producing the layout-aware IR (one element per non-empty
cell, `Row{r}.Col{c}` anchors), wired into `ingest/base.py`.
**Acceptance:** `test_ingest` loads a CSV fixture and extracts its questions.
Area: `ingest/`.

### 3. Per-reason counts in the CLI summary
After `answer`, print a one-line breakdown of flagged items by reason
(`unsupported: 2, ambiguous: 1, conflict: 1`).
**Acceptance:** a test on the summary string. Area: `cli.py`, `output/`.

### 4. `RERANKER_MODEL` / `EMBEDDING_MODEL` surfaced in `doctor`
When `--retrieval` is passed, print which model names were loaded and their
download status.
**Acceptance:** `test_doctor` asserts the model names appear in the checks.
Area: `llm/doctor.py`.

### 5. Markdown export of answers
Add `--format md` to `answer` to also emit `answered.md` (a clean Q/A list with
citations), alongside the existing outputs.
**Acceptance:** a test asserts `answered.md` is produced and contains a citation.
Area: `output/writer.py`, `cli.py`.

### 6. Configurable conflict similarity floor via CLI
Expose `--conflict-floor` on `answer` to override `conflict_similarity_floor`.
**Acceptance:** a test shows a lower floor surfaces an extra conflict.
Area: `cli.py`, `core/conflicts.py`.

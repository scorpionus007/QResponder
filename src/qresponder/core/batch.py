"""Batch processing (Part D).

Process many questionnaires in one go: each file runs through the existing
run_pipeline in isolation (one bad file never sinks the batch — it's reported),
each gets its own output set, and the batch produces a summary + a single zip.

Thin orchestration over run_pipeline + writer — no new answering logic.
"""

from __future__ import annotations

import json
import logging
import zipfile
from collections import Counter
from pathlib import Path

from ..config import Config
from ..llm.base import LLMProvider, make_provider
from ..models import Status
from ..output.writer import write_all
from .pipeline import run_pipeline

log = logging.getLogger("qresponder.batch")

_SUPPORTED = {".xlsx", ".xlsm", ".docx", ".pdf"}


def resolve_questionnaires(patterns: list[str]) -> list[Path]:
    """Expand directories and globs into a sorted, de-duplicated file list."""
    import glob as _glob

    found: list[Path] = []
    for pat in patterns:
        p = Path(pat)
        if p.is_dir():
            found += [c for c in sorted(p.iterdir()) if c.suffix.lower() in _SUPPORTED]
        elif any(ch in pat for ch in "*?[]"):
            found += [Path(m) for m in sorted(_glob.glob(pat)) if Path(m).suffix.lower() in _SUPPORTED]
        elif p.exists():
            found.append(p)
    # De-dup, preserve order.
    seen, out = set(), []
    for f in found:
        key = str(f.resolve())
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def _file_summary(result) -> dict:
    answered = [r for r in result.results if r.status == Status.ANSWERED]
    flagged = [r for r in result.results if r.status == Status.NEEDS_REVIEW]
    return {
        "total": len(result.results),
        "answered": len(answered),
        "flagged": len(flagged),
        "by_reason": dict(Counter(r.review_reason.value for r in flagged)),
    }


def run_batch(
    files: list,
    kb_dir: str | None,
    qa_path: str | None,
    config: Config,
    out_root: str | Path,
    scope_tags=None,
    evidence_dir: str | None = None,
    provider: LLMProvider | None = None,
    on_event=None,
    review_markers: bool = True,
) -> dict:
    """Run each file isolated; return a batch summary. Failures don't abort."""
    provider = provider or make_provider(config)
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    per_file = []
    for fp in files:
        fp = Path(fp)
        sub = out_root / fp.stem
        try:
            result = run_pipeline(str(fp), kb_dir, qa_path, config, scope_tags=scope_tags,
                                  provider=provider, evidence_dir=evidence_dir, on_event=on_event)
            write_all(result, sub, review_markers=review_markers)
            per_file.append({"file": fp.name, "ok": True, "out_dir": str(sub),
                             "summary": _file_summary(result)})
        except Exception as exc:  # noqa: BLE001 - isolate per-file failures
            log.warning("Batch file %s failed: %s", fp.name, exc)
            per_file.append({"file": fp.name, "ok": False, "error": str(exc)})

    summary = {
        "n_files": len(files),
        "succeeded": sum(1 for f in per_file if f["ok"]),
        "failed": sum(1 for f in per_file if not f["ok"]),
        "files": per_file,
    }
    (out_root / "batch_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def zip_batch(out_root: str | Path, zip_name: str = "batch_outputs.zip") -> str:
    """Bundle every per-file output + the batch summary into one zip."""
    root = Path(out_root)
    zip_path = root / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in sorted(root.rglob("*")):
            if fp.is_file() and fp.name != zip_name:
                zf.write(fp, str(fp.relative_to(root)))
    return str(zip_path)

"""Batch processing + ZIP tests (Part D). Offline."""

import shutil
import zipfile
from pathlib import Path

from qresponder.config import Config
from qresponder.core.batch import resolve_questionnaires, run_batch, zip_batch

FIX = Path(__file__).parent / "fixtures"


def test_resolve_questionnaires_dir_and_glob(tmp_path):
    shutil.copy(FIX / "sample.xlsx", tmp_path / "a.xlsx")
    shutil.copy(FIX / "sample.docx", tmp_path / "b.docx")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    found = resolve_questionnaires([str(tmp_path)])
    names = sorted(p.name for p in found)
    assert names == ["a.xlsx", "b.docx"]  # .txt excluded


def test_batch_isolates_failures_and_zips(tmp_path):
    # Two valid files + one malformed .xlsx (garbage bytes).
    shutil.copy(FIX / "sample.xlsx", tmp_path / "good1.xlsx")
    shutil.copy(FIX / "sample.xlsx", tmp_path / "good2.xlsx")
    (tmp_path / "broken.xlsx").write_bytes(b"not a real xlsx")

    files = resolve_questionnaires([str(tmp_path)])
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    out = tmp_path / "out"
    summary = run_batch(files, str(FIX / "kb"), str(FIX / "qa.yaml"), cfg, out, scope_tags=["soc2"])

    assert summary["n_files"] == 3
    assert summary["succeeded"] == 2
    assert summary["failed"] == 1
    # The bad file is reported, not fatal.
    broken = next(f for f in summary["files"] if f["file"] == "broken.xlsx")
    assert broken["ok"] is False and broken["error"]
    # Each good file produced an output set.
    assert (out / "good1" / "answered.xlsx").exists()
    assert (out / "good2" / "results.json").exists()
    assert (out / "batch_summary.json").exists()

    zpath = zip_batch(out)
    assert Path(zpath).exists()
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
    assert any("good1/answered.xlsx" in n.replace("\\", "/") for n in names)
    assert "batch_summary.json" in [n.replace("\\", "/") for n in names]

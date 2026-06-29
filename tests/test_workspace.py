"""Workspace storage + config resolution tests (Phase 5, F1)."""

from pathlib import Path

import pytest

from qresponder.config import Config
from qresponder.core.workspace import WorkspaceError, WorkspaceStore, slugify
from qresponder.kb.in_context import InContextKB
from qresponder.kb.tags import load_tag_sidecar, write_tag_sidecar


def test_slugify():
    assert slugify("Acme — SOC 2") == "acme-soc-2"
    assert slugify("  Hello World  ") == "hello-world"
    with pytest.raises(WorkspaceError):
        slugify("!!!")


def test_create_list_get_delete(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    ws = store.create("Acme SOC 2")
    assert ws.id == "acme-soc-2"
    assert ws.name == "Acme SOC 2"
    assert ws.kb_dir.is_dir() and ws.evidence_dir.is_dir() and ws.runs_dir.is_dir()
    assert ws.qa_path.exists() and ws.settings_path.exists()

    assert [w.id for w in store.list()] == ["acme-soc-2"]
    assert store.get("acme-soc-2").name == "Acme SOC 2"

    with pytest.raises(WorkspaceError):
        store.create("Acme SOC 2")  # duplicate slug

    store.delete("acme-soc-2")
    assert store.list() == []


def test_workspaces_are_isolated(tmp_path):
    store = WorkspaceStore(tmp_path / "ws")
    a = store.create("Client A")
    b = store.create("Client B")
    (a.kb_dir / "p.md").write_text("A policy", encoding="utf-8")
    (b.kb_dir / "p.md").write_text("B policy", encoding="utf-8")
    assert "A policy" in InContextKB.load(a.kb_dir).assemble_context()
    assert "B policy" not in InContextKB.load(a.kb_dir).assemble_context()


def test_effective_config_overrides_but_never_provider(tmp_path):
    store = WorkspaceStore(tmp_path / "ws")
    ws = store.create("W")
    store.update_settings("W".lower(), {"kb_mode": "retrieval", "detect_conflicts": False, "tags": ["soc2"]})
    cfg = ws.effective_config(Config(llm_provider="anthropic", anthropic_api_key="secret", kb_mode="in_context"))
    assert cfg.kb_mode == "retrieval"            # overridden
    assert cfg.detect_conflicts is False         # overridden
    assert cfg.llm_provider == "anthropic"       # provider untouched
    assert cfg.anthropic_api_key == "secret"     # key untouched
    assert ws.default_tags() == ["soc2"]


def test_settings_rejects_provider_and_key(tmp_path):
    store = WorkspaceStore(tmp_path / "ws")
    store.create("W")
    for bad in ({"anthropic_api_key": "x"}, {"llm_provider": "openai_compat"}, {"llm_model": "y"}):
        with pytest.raises(WorkspaceError):
            store.update_settings("w", bad)


def test_kb_tag_sidecar_scopes_retrieval(tmp_path):
    d = tmp_path / "kb"
    d.mkdir()
    (d / "enc.md").write_text("Data at rest is encrypted with AES-256.", encoding="utf-8")
    write_tag_sidecar(d, {"enc.md": ["soc2", "encryption"]})
    assert load_tag_sidecar(d)["enc.md"] == ["soc2", "encryption"]

    kb = InContextKB.load(d)
    chunk = next(c for c in kb.chunks if "AES-256" in c.text)
    assert "encryption" in chunk.tags                      # sidecar tag applied
    assert "AES-256" in kb.assemble_context(scope_tags=["soc2"])
    assert "AES-256" not in kb.assemble_context(scope_tags=["gdpr"])  # scoped out

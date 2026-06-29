"""Workspaces (Phase 5, F1) — named, isolated asset bundles.

A workspace is a directory under WORKSPACES_DIR (default ./workspaces) holding
its own kb/, evidence/, qa.yaml, settings.yaml (per-workspace engine config), and
runs/. settings.yaml overrides the GLOBAL config for that workspace — but the
provider and API key ALWAYS come from .env/global config, never per-workspace.

This is storage + config resolution only; it reimplements no engine logic.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel

from ..config import Config

# Engine settings a workspace may override. Provider/key fields are deliberately
# absent — they never live in a workspace.
ALLOWED_SETTINGS = {
    "kb_mode",
    "verify_faithfulness",
    "detect_conflicts",
    "conflict_use_judge",
    "conflict_similarity_floor",
    "strong_rerank_score",
    "strong_grounding_score",
    "batch_size",
    "top_n_retrieve",
    "top_k_context",
    "rrf_k",
    "max_kb_chars",
}
# Never settable through a workspace (would leak/override credentials).
FORBIDDEN_SETTINGS = {
    "llm_provider",
    "anthropic_api_key",
    "anthropic_model",
    "llm_base_url",
    "llm_api_key",
    "llm_model",
}


class WorkspaceError(ValueError):
    pass


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    if not slug:
        raise WorkspaceError("Workspace name must contain letters or digits.")
    return slug[:64]


class Workspace(BaseModel):
    id: str            # slug
    name: str
    dir: str
    created: str | None = None

    @property
    def path(self) -> Path:
        return Path(self.dir)

    @property
    def kb_dir(self) -> Path:
        return self.path / "kb"

    @property
    def evidence_dir(self) -> Path:
        return self.path / "evidence"

    @property
    def qa_path(self) -> Path:
        return self.path / "qa.yaml"

    @property
    def settings_path(self) -> Path:
        return self.path / "settings.yaml"

    @property
    def runs_dir(self) -> Path:
        return self.path / "runs"

    def load_settings(self) -> dict:
        if self.settings_path.exists():
            data = yaml.safe_load(self.settings_path.read_text(encoding="utf-8")) or {}
            return data if isinstance(data, dict) else {}
        return {}

    def default_tags(self) -> list[str]:
        tags = self.load_settings().get("tags") or []
        return [str(t).strip().lower() for t in tags if str(t).strip()]

    def effective_config(self, global_config: Config) -> Config:
        """Global config with this workspace's settings layered on top.
        Provider/key always stay from global — never overridden here."""
        cfg = global_config.model_copy()
        for key, value in self.load_settings().items():
            if key in ALLOWED_SETTINGS:
                setattr(cfg, key, value)
        return cfg


class WorkspaceStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _meta_path(self, slug: str) -> Path:
        return self.root / slug / "meta.yaml"

    def _from_dir(self, d: Path) -> Workspace | None:
        meta_file = d / "meta.yaml"
        if not meta_file.exists():
            return None
        meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        return Workspace(
            id=meta.get("slug", d.name),
            name=meta.get("name", d.name),
            dir=str(d),
            created=meta.get("created"),
        )

    def create(self, name: str) -> Workspace:
        slug = slugify(name)
        wdir = self.root / slug
        if wdir.exists():
            raise WorkspaceError(f"A workspace named '{name}' (slug '{slug}') already exists.")
        for sub in ("kb", "evidence", "runs"):
            (wdir / sub).mkdir(parents=True, exist_ok=True)
        (wdir / "qa.yaml").write_text("[]\n", encoding="utf-8")
        (wdir / "settings.yaml").write_text("", encoding="utf-8")
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._meta_path(slug).write_text(
            yaml.safe_dump({"slug": slug, "name": name, "created": created}, sort_keys=False),
            encoding="utf-8",
        )
        return self.get(slug)

    def list(self) -> list[Workspace]:
        if not self.root.exists():
            return []
        out = []
        for d in sorted(self.root.iterdir()):
            if d.is_dir():
                ws = self._from_dir(d)
                if ws is not None:
                    out.append(ws)
        return out

    def get(self, workspace_id: str) -> Workspace:
        ws = self._from_dir(self.root / workspace_id)
        if ws is None:
            raise WorkspaceError(f"Workspace '{workspace_id}' not found.")
        return ws

    def rename(self, workspace_id: str, name: str) -> Workspace:
        ws = self.get(workspace_id)
        meta = yaml.safe_load(self._meta_path(workspace_id).read_text(encoding="utf-8")) or {}
        meta["name"] = name
        self._meta_path(workspace_id).write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
        return self.get(workspace_id)

    def update_settings(self, workspace_id: str, updates: dict) -> dict:
        ws = self.get(workspace_id)
        forbidden = FORBIDDEN_SETTINGS & set(updates)
        if forbidden:
            raise WorkspaceError(
                f"These settings are not allowed in a workspace (provider/key stay in .env): "
                f"{', '.join(sorted(forbidden))}"
            )
        settings = ws.load_settings()
        for key, value in updates.items():
            if key in ALLOWED_SETTINGS or key == "tags":
                settings[key] = value
            else:
                raise WorkspaceError(f"Unknown setting '{key}'.")
        ws.settings_path.write_text(yaml.safe_dump(settings, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return settings

    def delete(self, workspace_id: str) -> None:
        ws = self.get(workspace_id)
        shutil.rmtree(ws.path)

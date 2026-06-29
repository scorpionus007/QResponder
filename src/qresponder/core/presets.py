"""Answer-style presets (Phase 7, Part A).

A preset is a named block of STYLE/FORMAT instructions injected into the answer
(and interpretation/decompose) prompts. Built-ins ship in code; workspaces add
custom presets in presets.yaml. Crucially, a preset shapes tone/length ONLY — it
can never relax grounding: the prompt makes explicit that style never overrides
the requirement to cite a supporting snippet or to abstain when unsupported.
"""

from __future__ import annotations

from pathlib import Path

import yaml

BUILTIN_PRESETS = {
    "concise": (
        "Be concise: 1–2 sentences, or a direct yes/no followed by a brief "
        "justification. Always include the supporting citation."
    ),
    "detailed": (
        "Be detailed: a fuller narrative that explains the control, how it is "
        "implemented, and any relevant scope — still grounded in and cited from "
        "the knowledge base."
    ),
    "formal": (
        "Use a formal compliance tone suitable for an auditor: precise, "
        "third-person, no marketing language. Ground and cite every claim."
    ),
}


def load_workspace_presets(workspace_dir: str | Path | None) -> dict:
    if not workspace_dir:
        return {}
    p = Path(workspace_dir) / "presets.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items() if v} if isinstance(data, dict) else {}


def all_presets(workspace_dir: str | Path | None = None) -> dict:
    """Built-ins plus workspace customs (customs win on name collision)."""
    return {**BUILTIN_PRESETS, **load_workspace_presets(workspace_dir)}


def resolve(name: str | None, workspace_dir: str | Path | None = None) -> str | None:
    """Return the style instructions for a preset name, or None if unset/unknown."""
    if not name:
        return None
    return all_presets(workspace_dir).get(name)


def save_workspace_preset(workspace_dir: str | Path, name: str, instructions: str) -> dict:
    p = Path(workspace_dir) / "presets.yaml"
    presets = {}
    if p.exists():
        presets = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(presets, dict):
        presets = {}
    presets[str(name)] = str(instructions)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(presets, sort_keys=True, allow_unicode=True), encoding="utf-8")
    return presets

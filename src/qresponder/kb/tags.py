"""Tag handling + tag-scoping (§5.3, Scrut L4).

Tag-scoping is what stops a GDPR question pulling SOC 2 evidence: the user
passes `--tags hipaa,soc2` and retrieval/library lookup are bounded to artifacts
carrying at least one of those tags. An artifact with NO tags is treated as
universal (always in scope) so an unlabeled KB still works.
"""

from __future__ import annotations

from pathlib import Path

import yaml

# Sidecar file mapping {filename: [tags]} the UI writes when a user tags a doc.
TAGS_SIDECAR = ".tags.yaml"


def load_tag_sidecar(directory: str | Path) -> dict[str, list[str]]:
    """Read a directory's `.tags.yaml` (file -> tags), if present."""
    p = Path(directory) / TAGS_SIDECAR
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return {str(k): normalize_tags(v) for k, v in data.items()}


def write_tag_sidecar(directory: str | Path, mapping: dict[str, list[str]]) -> None:
    p = Path(directory) / TAGS_SIDECAR
    p.parent.mkdir(parents=True, exist_ok=True)
    clean = {str(k): normalize_tags(v) for k, v in mapping.items() if normalize_tags(v)}
    p.write_text(yaml.safe_dump(clean, sort_keys=True, allow_unicode=True), encoding="utf-8")


def parse_tags(value: str | None) -> list[str]:
    """Parse a comma-separated tag string into a normalized list."""
    if not value:
        return []
    return [t.strip().lower() for t in value.split(",") if t.strip()]


def normalize_tags(tags) -> list[str]:
    if not tags:
        return []
    if isinstance(tags, str):
        return parse_tags(tags)
    return [str(t).strip().lower() for t in tags if str(t).strip()]


def source_allowed(source_name, artifact_tags, include, exclude) -> bool:
    """Per-run source include/exclude (Phase 10 C). `include`/`exclude` are sets
    of lowercased source names or tags. Exclude wins; an empty include = all."""
    name = (source_name or "").lower()
    tags = set(normalize_tags(artifact_tags))
    if exclude and (name in exclude or tags & exclude):
        return False
    if include:
        return name in include or bool(tags & include)
    return True


def in_scope(artifact_tags, scope_tags) -> bool:
    """True if the artifact is in scope for the given tag scope.

    Empty scope = everything in scope. Untagged artifact = always in scope.
    """
    scope = normalize_tags(scope_tags)
    if not scope:
        return True
    atags = normalize_tags(artifact_tags)
    if not atags:
        return True
    return bool(set(atags) & set(scope))

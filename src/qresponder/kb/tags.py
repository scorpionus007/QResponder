"""Tag handling + tag-scoping (§5.3, Scrut L4).

Tag-scoping is what stops a GDPR question pulling SOC 2 evidence: the user
passes `--tags hipaa,soc2` and retrieval/library lookup are bounded to artifacts
carrying at least one of those tags. An artifact with NO tags is treated as
universal (always in scope) so an unlabeled KB still works.
"""

from __future__ import annotations


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

"""Query normalization before retrieval (Part G3).

Lifts recall — especially the exact-term/BM25 matches we already win on — by:
  * expanding known acronyms from a small glossary (so an "MFA?" query also
    carries "multi-factor authentication" and matches the spelled-out KB chunk),
  * stripping boilerplate ("please describe", "do you…") that adds no signal.

The original text is always preserved (expansions are appended), so exact terms
still match. Offline, deterministic.
"""

from __future__ import annotations

import re

# A small built-in glossary of common security/GRC acronyms. Workspace/config
# `glossary` entries are merged on top.
DEFAULT_GLOSSARY = {
    "mfa": "multi-factor authentication",
    "sso": "single sign-on",
    "ir": "incident response",
    "dr": "disaster recovery",
    "bcp": "business continuity plan",
    "bcdr": "business continuity and disaster recovery",
    "rto": "recovery time objective",
    "rpo": "recovery point objective",
    "kms": "key management service",
    "tls": "transport layer security",
    "pii": "personally identifiable information",
    "dlp": "data loss prevention",
    "siem": "security information and event management",
    "vpn": "virtual private network",
    "rbac": "role-based access control",
    "soc 2": "soc 2 type ii service organization controls",
}

_BOILERPLATE = [
    r"^\s*please\s+(describe|provide|explain|detail|list|confirm|specify)\s+",
    r"^\s*(can|do|does|is|are|will|would|have|has)\s+(you|your|the\s+(company|organization|organisation|vendor))\s+",
    r"^\s*briefly\s+",
]


def normalize_query(text: str, glossary: dict | None = None) -> str:
    """Return a retrieval-friendly query: original text + acronym expansions,
    with leading boilerplate stripped."""
    if not text:
        return text
    merged = {**DEFAULT_GLOSSARY, **{str(k).lower(): str(v) for k, v in (glossary or {}).items()}}
    low = text.lower()
    expansions = []
    for acro, full in merged.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(acro)}(?![a-z0-9])", low) and full.lower() not in low:
            expansions.append(full)

    core = text
    for pat in _BOILERPLATE:
        core = re.sub(pat, "", core, flags=re.IGNORECASE)
    core = core.strip()

    parts = [text]
    if core and core.lower() != text.lower():
        parts.append(core)
    parts.extend(expansions)
    # De-dup while preserving order.
    seen, out = set(), []
    for p in parts:
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return " ".join(out)

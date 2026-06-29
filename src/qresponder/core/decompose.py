"""Compound-question decomposition (Part G2).

Detect multi-part items (multiple '?', semicolon/enumerated lists, or a trailing
"a, b, and c" list) and split them into sub-questions. Each sub-question is
answered grounded (reusing the interpretations machinery), then recomposed into a
structured answer with subanswers. If ANY sub-part is unsupported, the whole item
is NEEDS_REVIEW — no silently-dropped sub-question.
"""

from __future__ import annotations

import re


def split_parts(text: str) -> list[str]:
    t = (text or "").strip()
    if not t:
        return [t]

    # 1) Multiple explicit questions ("Do you A? Do you B?").
    pieces = [p.strip() for p in re.split(r"(?<=\?)\s+", t) if p.strip()]
    if len([p for p in pieces if p.endswith("?")]) >= 2:
        return pieces

    # 2) Semicolon-separated parts.
    if ";" in t:
        parts = [p.strip(" ;?") for p in t.split(";") if p.strip(" ;?")]
        if len(parts) >= 2:
            return [p if p.endswith("?") else p + "?" for p in parts]

    # 3) Trailing list: "stem ... a, b, and c?".
    body = t.rstrip("?")
    frags = [p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+", body) if p.strip()]
    if len(frags) >= 3:
        return [p if p.endswith("?") else p + "?" for p in frags]

    return [t]


def is_compound(text: str) -> bool:
    return len(split_parts(text)) >= 2

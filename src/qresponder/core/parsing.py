"""Model-agnostic defensive JSON parsing (§4.6, §14).

Weak local models wrap JSON in prose or code fences. We strip fences, try a
direct parse, then fall back to extracting the outermost array/object. Callers
decide what to do on persistent failure (extract raises; answer flags
NEEDS_REVIEW / parse_error).
"""

from __future__ import annotations

import json


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # Remove the opening fence (optionally ```json) and the closing fence.
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def parse_json_array(text: str) -> list:
    """Parse a JSON array from possibly-noisy model output. Raises ValueError."""
    t = _strip_fences(text)
    try:
        data = json.loads(t)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Fall back: slice the outermost [...] span.
    start, end = t.find("["), t.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(t[start : end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not parse a JSON array from model output.")

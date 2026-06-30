"""Live model lists (Phase 8 A) — server-side, key-gated, never hardcoded.

Calls each provider's models endpoint only when that provider's key is present,
parses exact model IDs, caches briefly, and returns a `reason` on failure rather
than substituting a guessed name. All calls are server-side; never from the
browser. The HTTP fetcher is injectable so the test suite stays offline.
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field

from .providers import PROVIDER_SPECS, base_url_for, canonical, is_configured, provider_key

_CACHE_TTL = 600.0  # seconds
_cache: dict[str, tuple[float, list]] = {}


@dataclass
class ModelInfo:
    id: str
    name: str | None = None
    created: int | None = None

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "created": self.created}


@dataclass
class ModelList:
    provider: str
    models: list = field(default_factory=list)
    reason: str | None = None


def _default_fetch(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 - server-side provider call
        return json.loads(resp.read().decode("utf-8"))


def _headers(provider: str, key: str) -> dict:
    if provider == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    return {"Authorization": f"Bearer {key}"}


def _parse(provider: str, data: dict) -> list[ModelInfo]:
    out: list[ModelInfo] = []
    # OpenAI / Gemini-compat / DeepSeek: {"data": [{"id": ...}]}; Anthropic:
    # {"data": [{"id": ..., "display_name": ...}]}.
    items = data.get("data") if isinstance(data, dict) else None
    if items is None and isinstance(data, dict):
        items = data.get("models")  # native Gemini shape, just in case
    for it in items or []:
        if not isinstance(it, dict):
            continue
        mid = it.get("id") or it.get("name")
        if not mid:
            continue
        mid = str(mid).split("/")[-1]  # strip "models/" prefix (Gemini native)
        out.append(ModelInfo(id=mid, name=it.get("display_name") or it.get("name"),
                             created=it.get("created")))
    # Prefer chat/generation models where the id makes it obvious; keep all otherwise.
    return out


def list_models(provider: str, config, fetch=None, use_cache: bool = True) -> ModelList:
    p = canonical(provider)
    spec = PROVIDER_SPECS.get(p)
    if spec is None:
        return ModelList(provider=p, reason=f"unknown provider '{provider}'")
    if not is_configured(config, p):
        return ModelList(provider=p, reason=f"not configured — set the {p} key in .env")

    if use_cache and p in _cache:
        ts, models = _cache[p]
        if time.monotonic() - ts < _CACHE_TTL:
            return ModelList(provider=p, models=list(models))

    url = spec["models"]["url"]
    if url is None:  # local: derive from the configured base URL
        base = (base_url_for(config, p) or "").rstrip("/")
        url = f"{base}/models"
    key = provider_key(config, p) or getattr(config, "llm_api_key", "") or ""
    fetch = fetch or _default_fetch
    try:
        data = fetch(url, _headers(p, key))
        models = _parse(p, data)
    except Exception as exc:  # noqa: BLE001 - report, never guess
        return ModelList(provider=p, reason=f"could not reach {spec['label']} model list: {exc}")

    if use_cache:
        _cache[p] = (time.monotonic(), models)
    return ModelList(provider=p, models=models)


def clear_cache() -> None:
    _cache.clear()


def reachable(provider: str, config, fetch=None) -> tuple[bool, str | None]:
    """Cheap liveness check: can we list models? Returns (active, reason)."""
    ml = list_models(provider, config, fetch=fetch, use_cache=False)
    if ml.reason:
        return False, ml.reason
    return True, None

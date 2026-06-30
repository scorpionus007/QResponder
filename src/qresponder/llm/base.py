"""LLM provider interface + shared retry helper (§4.5, §12).

GUARDRAIL: all core logic depends on the `LLMProvider` Protocol, never a
concrete SDK. Providers are constructed from Config in `factory()`.
"""

from __future__ import annotations

import time
from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str: ...


class ProviderError(RuntimeError):
    """Raised for provider misconfiguration or repeated call failure."""


def with_retry(fn: Callable[[], str], *, attempts: int = 2, base_delay: float = 1.0) -> str:
    """Call `fn` with one retry + linear backoff (§12: one retry+backoff).

    Re-raises the last exception wrapped in ProviderError on persistent failure.
    """
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - normalize to ProviderError
            last_exc = exc
            if i < attempts - 1:
                time.sleep(base_delay * (i + 1))
    raise ProviderError(f"LLM call failed after {attempts} attempt(s): {last_exc}") from last_exc


def make_provider(config) -> LLMProvider:
    """Construct the default provider from config.llm_provider (Phase 8: routes
    anthropic | openai | gemini | deepseek | local | mock via the registry)."""
    from .providers import PROVIDER_SPECS, canonical, make_provider_for

    p = canonical(config.llm_provider)
    if p != "mock" and p not in PROVIDER_SPECS:
        raise ProviderError(
            f"Unknown LLM_PROVIDER '{config.llm_provider}'. Use one of: "
            "anthropic, openai, gemini, deepseek, local, mock."
        )
    return make_provider_for(config, p, None)

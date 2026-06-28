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
    """Construct the configured provider. Switching providers needs no code change."""
    provider = (config.llm_provider or "").strip().lower()
    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=config.anthropic_api_key, model=config.anthropic_model
        )
    if provider in {"openai_compat", "openai", "openai-compat"}:
        from .openai_compat_provider import OpenAICompatProvider

        return OpenAICompatProvider(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
        )
    if provider == "mock":
        from .mock import MockProvider

        return MockProvider()

    raise ProviderError(
        f"Unknown LLM_PROVIDER '{config.llm_provider}'. "
        "Use 'anthropic', 'openai_compat', or 'mock'."
    )

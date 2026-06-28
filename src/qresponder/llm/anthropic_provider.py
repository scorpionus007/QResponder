"""Anthropic provider (§12). Imports the SDK lazily so the package installs and
imports without `anthropic` present (tests use MockProvider, no network)."""

from __future__ import annotations

from .base import ProviderError, with_retry


class AnthropicProvider:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is empty. Set it in .env or the environment."
            )
        self.model = model
        self._api_key = api_key
        self._client = None  # lazy

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - import guard
                raise ProviderError(
                    "The 'anthropic' package is not installed. "
                    'Install it with: pip install "qresponder[anthropic]"'
                ) from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        client = self._get_client()

        def _call() -> str:
            resp = client.messages.create(
                model=self.model,
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.content[0].text

        return with_retry(_call)

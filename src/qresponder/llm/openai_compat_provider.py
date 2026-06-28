"""OpenAI-compatible provider (§12).

One class, three config values — covers Ollama, vLLM, LM Studio, OpenAI,
OpenRouter, Together, Groq, Azure OpenAI. Local vs cloud is just a different
base URL. The `openai` SDK is imported lazily.
"""

from __future__ import annotations

from .base import ProviderError, with_retry


class OpenAICompatProvider:
    def __init__(self, base_url: str, api_key: str, model: str):
        if not base_url:
            raise ProviderError("LLM_BASE_URL is empty. Set it in .env or the environment.")
        if not model:
            raise ProviderError("LLM_MODEL is empty. Set it in .env or the environment.")
        self.base_url = base_url
        self.model = model
        # Some local servers (Ollama) accept any key; default to a placeholder.
        self._api_key = api_key or "not-needed"
        self._client = None  # lazy

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - import guard
                raise ProviderError(
                    "The 'openai' package is not installed. "
                    'Install it with: pip install "qresponder[openai]"'
                ) from exc
            self._client = OpenAI(base_url=self.base_url, api_key=self._api_key)
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
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""

        return with_retry(_call)

"""`qresponder doctor` preflight (§12.1).

Verifies an end-to-end setup so any stranger can confirm their config on either
path: provider constructs -> tiny completion succeeds (proves endpoint + model)
-> tiny JSON parse succeeds -> (retrieval mode) embeddings + reranker load.
Returns structured checks; the CLI renders ✅ / ❌ with actionable detail.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .base import make_provider


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


_TINY_SYSTEM = "Return ONLY a JSON object."
_TINY_USER = 'Return exactly this JSON and nothing else: {"ok": true}'


def _hint_for_error(config, err: str) -> str:
    low = err.lower()
    if "connection" in low or "refused" in low or "failed to establish" in low or "timed out" in low:
        if config.llm_provider == "openai_compat":
            return (
                f"Could not reach {config.llm_base_url}. Is the server running? "
                "For Ollama: run `ollama serve` and `ollama pull " + config.llm_model + "`."
            )
        return "Could not reach the API endpoint. Check network/base URL."
    if "api_key" in low or "authentication" in low or "401" in low or "unauthorized" in low:
        return "Authentication failed. Check your API key in .env."
    if "model" in low and ("not found" in low or "does not exist" in low or "404" in low):
        return "Model not found. Pull it (Ollama: `ollama pull <model>`) or fix the model name."
    return err


def run_doctor(config, provider=None, check_retrieval: bool | None = None) -> list[Check]:
    checks: list[Check] = []

    # 1. Provider constructs.
    if provider is None:
        try:
            provider = make_provider(config)
            checks.append(
                Check("provider", True, f"provider '{config.llm_provider}' constructed")
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(Check("provider", False, str(exc)))
            return checks  # nothing else can run
    else:
        checks.append(Check("provider", True, "provider supplied"))

    # 2. Tiny completion succeeds (proves endpoint + model reachable).
    completion: str | None = None
    try:
        completion = provider.complete(_TINY_SYSTEM, _TINY_USER, max_tokens=64)
        checks.append(Check("completion", True, "model returned a completion"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("completion", False, _hint_for_error(config, str(exc))))

    # 3. Tiny JSON parse succeeds (model-agnostic structured output works).
    if completion is not None:
        parsed_ok = False
        text = completion.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[-1] if "\n" in text else text
        try:
            json.loads(text)
            parsed_ok = True
        except json.JSONDecodeError:
            # Tolerate a model that wrapped JSON in prose: find the first object.
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    json.loads(text[start : end + 1])
                    parsed_ok = True
                except json.JSONDecodeError:
                    parsed_ok = False
        checks.append(
            Check(
                "json_parse",
                parsed_ok,
                "parsed JSON from completion"
                if parsed_ok
                else "model did not return parseable JSON (it may flag more for review)",
            )
        )

    # 4. Embeddings + reranker load (required only for retrieval mode).
    want_retrieval = (
        check_retrieval if check_retrieval is not None else (config.kb_mode == "retrieval")
    )
    if want_retrieval:
        try:
            from .embeddings import LocalEmbedder

            LocalEmbedder(config.embedding_model)._load()
            checks.append(Check("embeddings", True, f"loaded {config.embedding_model}"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check("embeddings", False, str(exc)))
        try:
            from .reranker import LocalReranker

            LocalReranker(config.reranker_model)._load()
            checks.append(Check("reranker", True, f"loaded {config.reranker_model}"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check("reranker", False, str(exc)))
    else:
        checks.append(
            Check(
                "retrieval",
                True,
                "skipped (kb_mode=in_context); set KB_MODE=retrieval to verify embeddings+reranker",
            )
        )

    return checks

"""Multi-provider + live model picker tests (Phase 8 A/B). Offline via fake fetch."""

import pytest

from qresponder.config import Config
from qresponder.llm import models as models_mod
from qresponder.llm.base import ProviderError
from qresponder.llm.models import list_models, reachable
from qresponder.llm.openai_compat_provider import OpenAICompatProvider
from qresponder.llm.providers import base_url_for, is_configured, make_provider_for


def setup_function():
    models_mod.clear_cache()


def _fake_fetch_factory():
    seen = {}

    def fetch(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}, {"id": "o3"}]}

    return fetch, seen


def test_list_models_requires_key_else_returns_reason():
    cfg = Config(openai_api_key="")  # not configured
    ml = list_models("openai", cfg, fetch=lambda u, h: {"data": []})
    assert ml.models == []
    assert ml.reason and "configured" in ml.reason.lower()


def test_list_models_fetches_when_configured():
    cfg = Config(openai_api_key="sk-test")
    fetch, seen = _fake_fetch_factory()
    ml = list_models("openai", cfg, fetch=fetch)
    assert [m.id for m in ml.models] == ["gpt-4o", "gpt-4o-mini", "o3"]
    assert ml.reason is None
    assert seen["url"].endswith("/v1/models")
    assert seen["headers"]["Authorization"] == "Bearer sk-test"


def test_gemini_and_deepseek_routes():
    cfg = Config(gemini_api_key="g", deepseek_api_key="d")
    fetch, _ = _fake_fetch_factory()
    assert list_models("gemini", cfg, fetch=fetch).reason is None
    assert list_models("deepseek", cfg, fetch=fetch).reason is None
    assert "generativelanguage.googleapis.com" in base_url_for(cfg, "gemini")
    assert base_url_for(cfg, "deepseek") == "https://api.deepseek.com"


def test_anthropic_models_uses_key_header():
    cfg = Config(anthropic_api_key="sk-ant")
    seen = {}

    def fetch(url, headers):
        seen.update(headers)
        return {"data": [{"id": "claude-opus-4-8", "display_name": "Claude Opus 4.8"}]}

    ml = list_models("anthropic", cfg, fetch=fetch)
    assert ml.models[0].id == "claude-opus-4-8"
    assert "x-api-key" in seen and "Authorization" not in seen


def test_make_provider_for_routes_to_adapter_and_base_url():
    cfg = Config(deepseek_api_key="d")
    prov = make_provider_for(cfg, "deepseek", "deepseek-chat")
    assert isinstance(prov, OpenAICompatProvider)
    assert prov.base_url == "https://api.deepseek.com"
    assert prov.model == "deepseek-chat"


def test_make_provider_for_blocks_unconfigured_no_mock():
    cfg = Config(openai_api_key="")
    with pytest.raises(ProviderError):
        make_provider_for(cfg, "openai", "gpt-4o")  # never silently mocks


def test_reachable_reflects_fetch():
    cfg = Config(openai_api_key="sk")
    ok, reason = reachable("openai", cfg, fetch=lambda u, h: {"data": [{"id": "gpt-4o"}]})
    assert ok and reason is None
    bad, why = reachable("openai", cfg, fetch=_raise)
    assert not bad and why


def _raise(url, headers):
    raise RuntimeError("connection refused")


def test_is_configured():
    assert is_configured(Config(openai_api_key="x"), "openai")
    assert not is_configured(Config(openai_api_key=""), "openai")
    assert is_configured(Config(), "local")  # local has a default base url
    assert is_configured(Config(), "mock")

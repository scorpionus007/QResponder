"""LLM layer tests — provider factory, mock behavior, retry (no network)."""

import json

import pytest

from qresponder.config import Config
from qresponder.llm import prompts
from qresponder.llm.base import ProviderError, make_provider, with_retry
from qresponder.llm.mock import MockProvider


def test_factory_selects_mock_and_errors_on_unknown():
    p = make_provider(Config(llm_provider="mock"))
    assert isinstance(p, MockProvider)
    with pytest.raises(ProviderError):
        make_provider(Config(llm_provider="nope"))


def test_factory_anthropic_requires_key():
    with pytest.raises(ProviderError):
        make_provider(Config(llm_provider="anthropic", anthropic_api_key=""))


def test_with_retry_succeeds_after_one_failure():
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("transient")
        return "ok"

    assert with_retry(flaky, base_delay=0) == "ok"
    assert state["n"] == 2


def test_with_retry_raises_provider_error():
    def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(ProviderError):
        with_retry(always_fail, base_delay=0)


def test_mock_scripted_responses():
    m = MockProvider(responses=["[]", "hi"])
    assert m.complete("s", "u") == "[]"
    assert m.complete("s", "u") == "hi"


def test_mock_extract_finds_questions():
    m = MockProvider()
    ir = (
        "- Security!A1 = Section 1: Data Protection  [merged,bold]\n"
        "- Security!B3 = Do you encrypt data at rest?\n"
        "- Security!B4 = Please attach your SOC 2 report.\n"
        "- Security!B5 = Company name\n"  # not a question -> skipped
    )
    out = json.loads(m.complete(prompts.EXTRACT_SYSTEM, ir))
    texts = {i["question_text"]: i for i in out}
    assert "Do you encrypt data at rest?" in texts
    assert texts["Do you encrypt data at rest?"]["answer_type"] == "yes_no"
    assert texts["Do you encrypt data at rest?"]["section"] == "Section 1: Data Protection"
    assert texts["Do you encrypt data at rest?"]["location_hint"] == "Security!B3"
    attach = next(i for i in out if "attach" in i["question_text"].lower())
    assert attach["answer_type"] == "attachment"
    assert "Company name" not in texts


def test_mock_answer_grounds_and_flags_unsupported():
    m = MockProvider()
    kb = "AES-256 encryption is used for all data at rest with keys in KMS."
    questions = [
        {"question_id": "q1", "question_text": "Do you encrypt data at rest?", "answer_type": "yes_no"},
        {"question_id": "q2", "question_text": "What is your backup retention schedule timeframe?", "answer_type": "text"},
    ]
    user = prompts.build_answer_user(kb, questions)
    out = {r["question_id"]: r for r in json.loads(m.complete(prompts.ANSWER_SYSTEM, user))}
    assert out["q1"]["status"] == "answered"
    assert out["q1"]["citations"], "answered items must cite"
    assert out["q2"]["status"] == "needs_review"
    assert out["q2"]["review_reason"] == "unsupported"
    assert not out["q2"]["citations"]

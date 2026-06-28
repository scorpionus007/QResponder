"""doctor preflight tests (no network — mock provider)."""

from qresponder.config import Config
from qresponder.llm.doctor import run_doctor
from qresponder.llm.mock import MockProvider


def test_doctor_all_green_with_mock():
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    checks = run_doctor(cfg, provider=MockProvider())
    by_name = {c.name: c for c in checks}
    assert by_name["provider"].ok
    assert by_name["completion"].ok
    assert by_name["json_parse"].ok
    assert by_name["retrieval"].ok  # skipped-but-ok in in_context mode


def test_doctor_reports_bad_provider():
    cfg = Config(llm_provider="anthropic", anthropic_api_key="")
    checks = run_doctor(cfg)  # constructs provider -> should fail on missing key
    assert checks[0].name == "provider"
    assert not checks[0].ok
    # No further checks run once the provider cannot be built.
    assert len(checks) == 1


def test_doctor_handles_completion_failure():
    class BoomProvider:
        def complete(self, system, user, *, max_tokens=4096, temperature=0.0):
            raise RuntimeError("Connection refused")

    cfg = Config(llm_provider="openai_compat")
    checks = run_doctor(cfg, provider=BoomProvider())
    completion = next(c for c in checks if c.name == "completion")
    assert not completion.ok
    assert "ollama" in completion.detail.lower() or "server running" in completion.detail.lower()

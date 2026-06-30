"""Web provider/status tests (Phase 8 A/B). Offline; no key ever returned."""

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qresponder.config import Config  # noqa: E402
from qresponder.web.app import create_app  # noqa: E402


def _fake_fetch(url, headers):
    return {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}


def test_providers_endpoint_lists_models_and_never_returns_key(tmp_path):
    cfg = Config(llm_provider="openai", openai_api_key="sk-ant-SECRET", anthropic_api_key="")
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    client = TestClient(create_app(cfg, model_fetch=_fake_fetch))
    body = client.get("/api/providers")
    assert body.status_code == 200
    data = {p["name"]: p for p in body.json()}
    assert data["openai"]["configured"] is True
    assert [m["id"] for m in data["openai"]["models"]] == ["gpt-4o", "gpt-4o-mini"]
    assert data["openai"]["reachable"] is True
    # Anthropic not configured -> reported, empty, with reason.
    assert data["anthropic"]["configured"] is False
    assert data["anthropic"]["models"] == []
    # No key anywhere in the response.
    assert "SECRET" not in body.text


def test_status_active_and_no_key(tmp_path):
    cfg = Config(llm_provider="openai", openai_api_key="sk-SECRET")
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    client = TestClient(create_app(cfg, model_fetch=_fake_fetch))
    st = client.get("/api/status").json()
    assert st["provider"] == "openai"
    assert st["active"] is True
    assert "SECRET" not in str(st)


def test_status_inactive_when_unreachable(tmp_path):
    def boom(url, headers):
        raise RuntimeError("connection refused")

    cfg = Config(llm_provider="openai", openai_api_key="sk")
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    client = TestClient(create_app(cfg, model_fetch=boom))
    st = client.get("/api/status").json()
    assert st["active"] is False
    assert st["reason"]


def test_run_blocked_on_unconfigured_provider_no_mock(tmp_path):
    """Part B: an unconfigured provider blocks the run (400), never auto-mocks."""
    cfg = Config(llm_provider="anthropic", anthropic_api_key="")  # not configured
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    client = TestClient(create_app(cfg))
    wid = client.post("/api/workspaces", json={"name": "W"}).json()["id"]
    fix = Path(__file__).parent / "fixtures" / "sample.xlsx"
    with open(fix, "rb") as fh:
        resp = client.post(f"/api/workspaces/{wid}/runs",
                           files={"questionnaire": ("sample.xlsx", fh.read())})
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"].lower()

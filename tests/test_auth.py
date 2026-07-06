"""Optional opt-in access control (Phase 16). Default = no auth (local); when
QRESPONDER_AUTH_TOKEN is set, every request must carry it. Offline."""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qresponder.config import Config  # noqa: E402
from qresponder.web.app import create_app  # noqa: E402


def _app(tmp_path, **kw):
    cfg = Config(llm_provider="mock", kb_mode="in_context", **kw)
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    return TestClient(create_app(cfg))


def test_no_auth_by_default(tmp_path):
    client = _app(tmp_path)  # no token configured
    assert client.get("/api/status").status_code == 200


def test_token_gates_when_set(tmp_path):
    client = _app(tmp_path, auth_token="s3cret-token")
    # Without the token → 401 on API and the app.
    assert client.get("/api/status").status_code == 401
    assert client.get("/").status_code == 401
    # With the Bearer header → allowed, and no token echoed.
    r = client.get("/api/status", headers={"Authorization": "Bearer s3cret-token"})
    assert r.status_code == 200
    # Wrong token → still blocked.
    assert client.get("/api/status", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_query_token_sets_cookie(tmp_path):
    client = _app(tmp_path, auth_token="s3cret-token")
    r = client.get("/api/status?token=s3cret-token")
    assert r.status_code == 200
    # The cookie persists so subsequent requests pass without the query param.
    assert client.get("/api/status").status_code == 200
    # The token value isn't exposed in the body.
    assert "s3cret-token" not in client.get("/api/status").text

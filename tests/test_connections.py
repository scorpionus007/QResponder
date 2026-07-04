"""Prowler-style Connections (Phase 14) — offline. The headline guarantee: a secret
never appears in any list/GET/response/log, only status. All SaaS calls are mocked."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from qresponder.core.connections import ConnectionStore, build_connector

FIX = Path(__file__).parent / "fixtures"


# ---- store: secret lives apart from the record --------------------------------

def test_store_keeps_secret_out_of_the_record(tmp_path):
    store = ConnectionStore(tmp_path / "ws")
    conn = store.create("notion", "Eng Notion", config={"database": "db1", "token": "SHOULD-BE-STRIPPED"},
                        secret={"token": "super-secret-tok"})
    # The non-secret record never carries a token, even one smuggled into config.
    dumped = conn.model_dump_json()
    assert "super-secret-tok" not in dumped and "SHOULD-BE-STRIPPED" not in dumped
    assert conn.config == {"database": "db1"}
    # The secret is retrievable server-side only.
    assert store.get_secret(conn.id) == {"token": "super-secret-tok"}
    # Delete removes both.
    store.delete(conn.id)
    assert store.get(conn.id) is None and store.get_secret(conn.id) is None


def test_build_connector_probe_caps_items():
    c = build_connector("notion", {"database": "d"}, {"token": "t"},
                        client=lambda target: [{"name": f"d{i}", "text": "x"} for i in range(50)], probe=True)
    assert len(c.fetch()) == 3  # probe cap


# ---- web (offline) ------------------------------------------------------------
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qresponder.config import Config  # noqa: E402
from qresponder.web.app import create_app  # noqa: E402

KB_MD = "Tags: soc2\n\nWe encrypt data at rest with AES-256."


def _client(tmp_path, **kw):
    cfg = Config(llm_provider="mock", kb_mode="in_context", **kw)
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    cfg.extra["oauth_dir"] = str(tmp_path / "oauth")
    app = create_app(cfg)
    return app, TestClient(app)


def _wid(client):
    return client.post("/api/workspaces", json={"name": "W"}).json()["id"]


def test_create_token_connection_never_returns_secret(tmp_path):
    app, client = _client(tmp_path)
    wid = _wid(client)
    r = client.post(f"/api/workspaces/{wid}/connections",
                    json={"type": "notion", "label": "Eng", "config": {"database": "db1"}, "token": "tok-XYZ-secret"})
    assert r.status_code == 200
    assert "tok-XYZ-secret" not in r.text  # not echoed after entry
    cid = r.json()["connection"]["id"]
    # Not in the list, not in the single GET.
    lst = client.get(f"/api/workspaces/{wid}/connections")
    assert "tok-XYZ-secret" not in lst.text
    assert lst.json()["connections"][0]["label"] == "Eng"
    assert "token" not in lst.json()["connections"][0]
    # But it is usable server-side (test connection via injected client).
    app.state.connector_client = lambda target: [{"name": "policy", "text": "AES-256 at rest."}]
    t = client.post(f"/api/workspaces/{wid}/connections/{cid}/test").json()
    assert t["ok"] is True


def test_ephemeral_test_before_save_does_not_persist(tmp_path):
    app, client = _client(tmp_path)
    wid = _wid(client)
    app.state.connector_client = lambda target: [{"name": "p", "text": "hello"}]
    r = client.post(f"/api/workspaces/{wid}/connections/test",
                    json={"type": "confluence", "config": {"space": "ENG"}, "token": "ephemeral-secret"})
    assert r.json()["ok"] is True
    assert "ephemeral-secret" not in r.text
    # Nothing was saved by a mere test.
    assert client.get(f"/api/workspaces/{wid}/connections").json()["connections"] == []


def test_test_reports_failure_via_mocked_client(tmp_path):
    app, client = _client(tmp_path)
    wid = _wid(client)
    def boom(target):
        raise RuntimeError("401 unauthorized")
    app.state.connector_client = boom
    cid = client.post(f"/api/workspaces/{wid}/connections",
                      json={"type": "notion", "config": {"database": "d"}, "token": "t"}).json()["connection"]["id"]
    res = client.post(f"/api/workspaces/{wid}/connections/{cid}/test").json()
    assert res["ok"] is False and "401" in res["detail"]


def test_sync_ingests_into_kb_with_provenance_and_tags(tmp_path):
    app, client = _client(tmp_path)
    wid = _wid(client)
    app.state.connector_client = lambda target: [{"name": "Security Policy", "text": "We encrypt at rest with AES-256."}]
    cid = client.post(f"/api/workspaces/{wid}/connections",
                      json={"type": "notion", "config": {"database": "db1", "tags": ["soc2"]}, "token": "t"}).json()["connection"]["id"]
    r = client.post(f"/api/workspaces/{wid}/connections/{cid}/sync").json()
    assert r["ingested"] == 1 and r["last_synced"]
    # It landed in the workspace KB (with provenance) and is answerable via the KB.
    from qresponder.kb.in_context import InContextKB

    kb_dir = Path(tmp_path) / "ws" / wid / "kb"
    ctx = InContextKB.load(kb_dir).assemble_context(scope_tags=["soc2"])
    assert "AES-256" in ctx


def test_folder_connection_test_and_sync(tmp_path):
    app, client = _client(tmp_path)
    wid = _wid(client)
    src = tmp_path / "docs"
    src.mkdir()
    (src / "p.md").write_text("Tags: soc2\n\nMFA is enforced.", encoding="utf-8")
    cid = client.post(f"/api/workspaces/{wid}/connections",
                      json={"type": "folder", "config": {"path": str(src), "tags": ["soc2"]}}).json()["connection"]["id"]
    assert client.post(f"/api/workspaces/{wid}/connections/{cid}/test").json()["ok"] is True
    assert client.post(f"/api/workspaces/{wid}/connections/{cid}/sync").json()["ingested"] == 1


def test_oauth_connection_flow_stores_token_server_side(tmp_path):
    app, client = _client(tmp_path, notion_client_id="nid", notion_client_secret="sec")
    wid = _wid(client)
    app.state.oauth_fetch = lambda url, data, headers: {"access_token": "oauth-tok-secret"}
    start = client.get(f"/api/workspaces/{wid}/connections/notion/authorize?label=Eng+Notion").json()
    assert "oauth-tok-secret" not in start["authorize_url"]  # only client_id/pkce in the URL
    state = parse_qs(urlparse(start["authorize_url"]).query)["state"][0]
    cb = client.get(f"/api/oauth/callback?code=abc&state={state}")
    assert cb.status_code == 200 and "Connected" in cb.text
    # A connection now exists, connected, with NO token in the response.
    conns = client.get(f"/api/workspaces/{wid}/connections").json()["connections"]
    assert len(conns) == 1 and conns[0]["type"] == "notion" and conns[0]["status"] == "connected"
    assert "oauth-tok-secret" not in client.get(f"/api/workspaces/{wid}/connections").text
    # The token is usable server-side for a sync (injected connector client).
    app.state.connector_client = lambda target: [{"name": "d", "text": "AES-256 at rest."}]
    cid = conns[0]["id"]
    client.patch(f"/api/workspaces/{wid}/connections/{cid}", json={"config": {"database": "db1"}})
    assert client.post(f"/api/workspaces/{wid}/connections/{cid}/sync").json()["ingested"] == 1

"""Confluence connector (Phase 12) — extras-gated, injectable client, offline-tested.

Fetches pages from one user-specified Confluence space using the user's own API
token (server-side config, never the browser), and ingests them via the existing
bulk path. The base URL is SSRF-guarded; the real client is lazy-imported so the
slim image and import-guard hold. Runs only on explicit `connect confluence`.
"""

from __future__ import annotations

from .base import ConnectorError, TokenConnector


# The OAuth (3LO) gateway; paths below are the Confluence Cloud REST API **v2**
# (v1 /rest/api is retired → HTTP 410). v2 uses cursor pagination via _links.next.
_GATEWAY = "https://api.atlassian.com/ex/confluence"


def _cloud_get(cloud_id: str, token: str, path: str, timeout: int = 15):  # pragma: no cover - real network
    import json
    import urllib.request

    url = f"{_GATEWAY}/{cloud_id}{path}"  # path includes the full /wiki/api/v2/... prefix
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _paged(cloud_id: str, token: str, path: str, fetch, cap: int) -> list[dict]:
    """Follow v2 cursor pagination (data._links.next) up to `cap` items."""
    fetch = fetch or _cloud_get
    out: list[dict] = []
    while path and len(out) < cap:
        data = fetch(cloud_id, token, path)
        out.extend(data.get("results", []))
        nxt = (data.get("_links") or {}).get("next")
        path = nxt or None  # next is a site-relative path like /wiki/api/v2/...
    return out[:cap]


def list_spaces(token: str, cloud_id: str, fetch=None, max_spaces: int = 500) -> list[dict]:
    """List the spaces the signed-in user can see: [{key, name, id}]. `fetch(cloud_id,
    token, path) -> dict` is injectable so tests stay offline. Confluence REST v2."""
    rows = _paged(cloud_id, token, "/wiki/api/v2/spaces?limit=100", fetch, max_spaces)
    return [{"key": s.get("key"), "name": s.get("name") or s.get("key"), "id": s.get("id")} for s in rows]


class ConfluenceConnector(TokenConnector):
    service = "Confluence"
    env_hint = "set confluence_token (+ confluence_base_url, confluence_email) in .env"
    default_ext = ".html"  # Confluence storage format is HTML; the KB loader reads it

    def __init__(self, space_key: str, token=None, base_url=None, email=None, cloud_id=None,
                 tags=None, client=None, timeout: int = 15, max_items: int = 200):
        super().__init__(space_key, token=token, base_url=base_url, tags=tags,
                         client=client, timeout=timeout, max_items=max_items)
        self.email = email
        self.cloud_id = cloud_id  # set → use the OAuth (3LO) Bearer + Cloud API path

    def _make_client(self):  # pragma: no cover - real network/SDK path
        if self.cloud_id:
            return self._oauth_client()
        if not self.base_url:
            raise ConnectorError("Confluence: sign in with Confluence, or set confluence_base_url in .env.")
        try:
            from atlassian import Confluence  # type: ignore
        except ImportError as exc:
            raise ConnectorError(
                'Confluence needs the optional extra: pip install "qresponder[connectors]".'
            ) from exc
        api = Confluence(url=self.base_url, username=self.email, password=self.token, timeout=self.timeout)

        def _client(space_key: str):
            docs, start, limit = [], 0, 50
            while len(docs) < self.max_items:
                batch = api.get_all_pages_from_space(space_key, start=start, limit=limit,
                                                     expand="body.storage")
                if not batch:
                    break
                for p in batch:
                    docs.append({"name": p.get("title"), "text": (p.get("body", {}).get("storage", {}) or {}).get("value", ""),
                                 "url": f"{self.base_url}/pages/{p.get('id')}"})
                if len(batch) < limit:
                    break
                start += limit
            return docs

        return _client

    def _oauth_client(self):  # pragma: no cover - real network path
        """OAuth 2.0 (3LO): Bearer token against the Confluence Cloud REST API v2."""
        def _client(space_key: str):
            # v2 addresses pages by numeric space id, so resolve the key first.
            spaces = _paged(self.cloud_id, self.token,
                            f"/wiki/api/v2/spaces?keys={space_key}&limit=1", None, 1)
            if not spaces:
                return []
            sid = spaces[0].get("id")
            pages = _paged(self.cloud_id, self.token,
                           f"/wiki/api/v2/spaces/{sid}/pages?body-format=storage&limit=100",
                           None, self.max_items)
            docs = []
            for p in pages:
                body = ((p.get("body") or {}).get("storage") or {}).get("value", "")
                docs.append({"name": p.get("title"), "text": body,
                             "url": (p.get("_links") or {}).get("webui", "")})
            return docs

        return _client

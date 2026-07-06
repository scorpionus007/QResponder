# Source connectors

Pull documents from where they live into a workspace's knowledge base. Everything
goes through the same validation / sandbox / provenance / tagging as a manual upload
— connectors never reimplement ingestion.

**The boundary, always:** connector credentials live on the **server** (`.env`), the
client secret and access/refresh tokens are **never sent to the browser**, and a
connector fetches **only** when you explicitly Test or Sync — never during answering.

Add and manage connections in the UI at **Knowledge Base → Documents & sources →
Connections** (or the **Connections** rail item), or via the CLI
(`qresponder connect …`).

## No-credential connectors (work out of the box)

| Source | Fields | Notes |
| --- | --- | --- |
| **Folder** | path | Path-contained; only files under the folder are read. |
| **Website** | URL, depth, max-pages | Bounded same-domain crawl; **SSRF guard** rejects localhost/private/link-local/metadata IPs. |

## OAuth connectors (one-time app registration)

Each needs an OAuth app you register once with the provider; put the **client
id/secret** in `.env` (server-side). Redirect URI for every provider:
`http://127.0.0.1:8000/api/oauth/callback` (set `OAUTH_REDIRECT_BASE` if your host
differs). Then, in the UI, pick the source and click **Sign in with …** — you approve
in a new tab and the token is exchanged + stored server-side. Tokens auto-refresh on
expiry.

| Source | Register at | `.env` | Scopes |
| --- | --- | --- | --- |
| **Notion** | notion.so → My integrations → **Public** integration | `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET` | (integration-level) |
| **Google Drive** | Google Cloud Console → OAuth client (Drive API) | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | `drive.readonly` (offline access) |
| **Confluence** | Atlassian developer console → OAuth 2.0 (3LO) | `CONFLUENCE_CLIENT_ID`, `CONFLUENCE_CLIENT_SECRET` | `read:space:confluence`, `read:page:confluence`, `offline_access` |
| **SharePoint** | Microsoft Entra ID app | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` | `Sites.Read.All`, `Files.Read.All`, `offline_access` |
| **OneDrive** | Microsoft Entra ID app (same app as SharePoint) | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` | `Files.Read.All`, `offline_access` |

SharePoint and OneDrive share one Microsoft app (both use Microsoft Graph).

You can also skip OAuth and paste a **personal token** into `.env`
(`NOTION_TOKEN`, `CONFLUENCE_TOKEN`+`CONFLUENCE_BASE_URL`, `MICROSOFT_TOKEN`) — the
Add-Connection form will show a token field instead of a sign-in button.

## Live-verification checklist

CI can't exercise live SaaS calls (the tests use real-API-shaped mocks). Verify each
connector against the real service once, manually:

1. **Register** the OAuth app (table above); set the redirect URI to
   `<your server>/api/oauth/callback`.
2. Put the **client id/secret** in `.env` and (re)start the app.
3. In the UI: **Connections → + Add Connection → <source>**.
   - OAuth source → **Sign in with …** → approve in the new tab → it shows
     **connected**.
   - Token source → paste the token → **Test connection** must go green.
4. Set the target (Notion database id · Drive folder id · Confluence space key ·
   SharePoint site id · OneDrive folder path) and **Test** — expect a green result.
5. **Sync now** → confirm it reports "ingested N document(s)".
6. Go to **Knowledge Base → Documents & sources** and confirm the docs are there;
   then **Ask** a question they cover and confirm a grounded, cited answer.

If Test fails, the message is non-secret and usually points at a missing scope or the
wrong target id. Nothing in step 6 (answering) ever triggers a connector fetch.

## Per-provider notes

- **Notion**: uses `api.notion.com/v1` with the `Notion-Version` header; queries the
  database, reads each page's block children, paginates via `start_cursor`.
- **Google Drive**: Drive API v3 `files.list` scoped to the folder (pageToken);
  downloads text via `files.get?alt=media` and exports Google-native docs via
  `files.export` to `text/plain`.
- **Microsoft (SharePoint/OneDrive)**: Microsoft Graph `.../drive/root/children`,
  paginates `@odata.nextLink`, downloads textual items via `/content`.
- **Confluence**: Confluence Cloud REST **v2** (v1 is retired) via
  `api.atlassian.com/ex/confluence/{cloudId}`; the cloud id is resolved at sign-in.

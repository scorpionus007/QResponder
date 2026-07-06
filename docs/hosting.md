# Hosting QRESPONDER (optional — the default is local-only)

QRESPONDER is a **local, single-user tool** by default: it binds `127.0.0.1`, has
**no authentication**, and nothing leaves the host. That's the intended way to run
it. This page is only for the *optional* case where you deliberately want to reach it
from another machine.

> ⚠ **A no-auth instance on a network exposes your entire knowledge base.** Anyone
> who can reach the port can read every document, answer, and connection status.
> Do **not** bind to `0.0.0.0` or publish it without **both** a reverse proxy with
> TLS **and** the auth token (or the proxy's own auth) in front.

## 1. Turn on the optional access token

Set an env var (any long random string). When it's set, **every** request to the app
and API must carry it; when it's unset (default), there's no auth.

```bash
export QRESPONDER_AUTH_TOKEN="$(openssl rand -hex 24)"
```

Ways to supply it:
- **Header** (recommended, e.g. injected by a proxy): `Authorization: Bearer <token>`
- **First load in a browser**: open `https://your-host/?token=<token>` once — the app
  sets an `httponly`, `samesite=strict` cookie and subsequent requests pass.

The token is compared in constant time and never appears in a response body or log.
It is **not** a substitute for TLS + a proxy — it's a second layer.

## 2. Put a reverse proxy with TLS in front

Run the app bound to loopback (or a private interface) and let the proxy terminate
TLS and (optionally) add its own auth.

### Caddy (simplest — automatic TLS)

```caddy
qresponder.example.com {
    reverse_proxy 127.0.0.1:8000
    # Optional: proxy-level basic auth on top of the app token.
    basic_auth {
        # generate with: caddy hash-password
        admin <bcrypt-hash>
    }
    # Inject the app token so the browser never needs it:
    reverse_proxy 127.0.0.1:8000 {
        header_up Authorization "Bearer {env.QRESPONDER_AUTH_TOKEN}"
    }
}
```

### nginx

```nginx
server {
    listen 443 ssl;
    server_name qresponder.example.com;
    ssl_certificate     /etc/letsencrypt/live/qresponder.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qresponder.example.com/privkey.pem;

    auth_basic "QRESPONDER";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Authorization "Bearer ${QRESPONDER_AUTH_TOKEN}";
        proxy_set_header Host $host;
    }
}
```

### Traefik

Use a `Host()` router with a TLS resolver and a `basicauth` middleware, forwarding to
the container on the loopback network. Add a headers middleware to inject the
`Authorization: Bearer` token.

## 3. Run the container bound to the proxy only

In `docker-compose.yml`, keep the port mapped to loopback (`127.0.0.1:8000:8000`) and
put the proxy on the same host, or use an internal Docker network so the app port is
never published to the outside at all.

## What still holds when hosted

- **Answering is still local**: with a local model + local embeddings/reranker the
  answering path makes **zero external calls**. Cloud provider keys (if you use one)
  stay in `.env` on the server, never sent to the browser.
- **Connector secrets stay server-side** and are never returned to the browser.
- Connectors fetch **only** on explicit test/sync — never during answering.

If any of those matter to you, prefer the local default and reach it over SSH port-
forwarding (`ssh -L 8000:127.0.0.1:8000 host`) instead of exposing it at all.

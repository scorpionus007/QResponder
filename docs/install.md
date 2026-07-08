# Install

## Docker (one command — recommended)

```bash
curl -fsSLO https://raw.githubusercontent.com/scorpionus007/QResponder/main/docker-compose.yml
curl -fsSLO https://raw.githubusercontent.com/scorpionus007/QResponder/main/.env.example
mv .env.example .env        # optional — a local model needs no key
docker compose up -d        # → open http://localhost:8000
```

The port is published to your host's **loopback only** (`127.0.0.1:8000`). Workspaces
persist in the `qr-workspaces` volume.

**Fully local, zero cloud (no API key):**

```bash
docker compose --profile local up -d
docker compose exec ollama ollama pull llama3.1
# then in .env: LLM_PROVIDER=openai_compat, LLM_BASE_URL=http://ollama:11434/v1,
#               LLM_API_KEY=ollama, LLM_MODEL=llama3.1  → docker compose up -d
```

Or pull the published image directly:

```bash
docker run --rm -p 127.0.0.1:8000:8000 -v qr-data:/data \
  -e LLM_PROVIDER=mock ghcr.io/scorpionus007/qresponder:latest
```

## From source (Python 3.10+)

```bash
git clone https://github.com/scorpionus007/QResponder
cd QResponder
pip install -e ".[web,retrieval]"      # add ,dev to run the test suite
qresponder serve                        # → http://127.0.0.1:8000
```

Extras: `web` (FastAPI UI), `retrieval` (sentence-transformers/torch for full dense
hybrid retrieval + rerank; retrieval mode falls back to BM25 without it),
`anthropic` / `openai` (cloud SDKs), `connectors` (SaaS connector SDKs). Install only
what you need.

Run the offline test suite with `pip install -e ".[web,retrieval,dev]" && pytest -q`.

> **pip / pipx:** a published PyPI package (`pipx install qresponder`) is coming
> soon. For now, use Docker (above) or this from-source install.

## Configuration

Copy `.env.example` to `.env`. A local model (Ollama/vLLM/LM Studio) needs no key.
For a cloud model, set the provider's key — it stays server-side and is never sent to
the browser. See [connectors.md](connectors.md) for source-connector credentials and
[hosting.md](hosting.md) for exposing it on a network.

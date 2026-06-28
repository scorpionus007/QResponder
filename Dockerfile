# QRESPONDER — Phase 0 image.
# Core loop + both cloud/local provider SDKs. The Phase 1 retrieval extra
# (sentence-transformers/torch) is large and intentionally left out of the
# default image; add it with: pip install ".[retrieval]".
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --upgrade pip && pip install ".[anthropic,openai]"

# Default working area for mounted questionnaires / KB / output.
VOLUME ["/data"]

ENTRYPOINT ["qresponder"]
CMD ["--help"]

# QRESPONDER image.
#
# Extras are parametrized so you can build the mode you need:
#   default (in-context, both provider SDKs):
#       docker build -t qresponder .
#   retrieval-capable (--mode retrieval works in-container):
#       docker build --build-arg EXTRAS=anthropic,openai,retrieval -t qresponder:retrieval .
# The retrieval extra (sentence-transformers/torch) is large, so it is opt-in.
FROM python:3.12-slim

ARG EXTRAS=anthropic,openai

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --upgrade pip && pip install ".[${EXTRAS}]"

# Default working area for mounted questionnaires / KB / output.
VOLUME ["/data"]

ENTRYPOINT ["qresponder"]
CMD ["--help"]

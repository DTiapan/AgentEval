# Multi-stage security-hardened Dockerfile for AgentEval
# Stage 1: Build Web Console static assets
FROM node:20-slim AS web-builder

WORKDIR /build/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

# Stage 2: Build Python dependencies and virtual environment
FROM python:3.11-slim-bookworm AS py-builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install astral uv for fast dependency resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml README.md ./
COPY agenteval/ ./agenteval/
COPY agenteval_packs/ ./agenteval_packs/

RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache ".[api,inspect,postgres]"

# Stage 3: Minimal unprivileged runtime image
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    HOST=0.0.0.0 \
    AGENTEVAL_DATA_DIR=/app/data \
    AGENTEVAL_USE_SQLITE=1 \
    AGENTEVAL_SERVE_UI=1 \
    AGENTEVAL_UI_DIST=/app/web/dist

WORKDIR /app

# Create unprivileged service user for runtime security hardening
RUN groupadd -g 10001 agenteval && \
    useradd -u 10001 -g agenteval -s /bin/bash -m agenteval && \
    mkdir -p /app/data /app/data/suites /app/web/dist /app/cache /app/.agenteval && \
    chown -R agenteval:agenteval /app

# Copy virtual environment from builder
COPY --from=py-builder /opt/venv /opt/venv

# Copy compiled React Web Console assets from node builder
COPY --from=web-builder --chown=agenteval:agenteval /build/web/dist /app/web/dist

# Copy application packages and manifests
COPY --chown=agenteval:agenteval agenteval/ ./agenteval/
COPY --chown=agenteval:agenteval agenteval_packs/ ./agenteval_packs/
COPY --chown=agenteval:agenteval pyproject.toml README.md ./

USER agenteval

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8080'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

ENTRYPOINT ["python", "-m", "agenteval.cli.main", "serve"]
CMD ["--host", "0.0.0.0", "--port", "8080", "--with-ui"]

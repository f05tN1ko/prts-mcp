# syntax=docker/dockerfile:1
#
# Hosting image for the ModelScope MCP 广场 ("可托管部署") / generic PaaS builders.
#
# This is NOT the canonical development or CI image — that one stays at
# python/Dockerfile and is what .github/workflows/{ci,cd}.yml build with an
# explicit `-f python/Dockerfile`. This root-level Dockerfile exists because
# platform hosts look for `./Dockerfile` in the repository root and cannot be
# told to use a subdirectory path.
#
# Build (from the repository root):
#   docker build -t prts-mcp-hosted .
#
# Smaller/faster build that relies on runtime auto-sync instead of baked data:
#   docker build --build-arg PREFETCH_DATA=0 -t prts-mcp-hosted .
#
# Default transport is stdio, matching the convention used by ModelScope's own
# MCP server (modelscope/modelscope-mcp-server), whose hosted image also has a
# stdio entrypoint and no exposed port. For a self-hosted HTTP endpoint instead:
#   docker run -i --rm -e PRTS_TRANSPORT=http -e PORT=3000 -p 3000:3000 prts-mcp-hosted

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PRTS_MCP_ROOT=/app \
    PRTS_TRANSPORT=stdio \
    IMAGES_ENABLED=false \
    GITHUB_MIRRORS=https://ghproxy.net

WORKDIR /app

# Non-root runtime user. /app is read-only at runtime (PYTHONDONTWRITEBYTECODE
# keeps bytecode out of it); only /data is written to, and it is chown'd below.
RUN useradd --create-home --uid 1000 prts

# --- Python package -------------------------------------------------------
# pyproject.toml lives in python/, so install that directory directly rather
# than flattening it to the build root the way python/Dockerfile does.
COPY python/pyproject.toml python/README.md ./python/
COPY python/src/ ./python/src/
RUN pip install ./python

# --- Bundled data (offline baseline) --------------------------------------
# data/gamedata ships the four operator tables in-tree (~30 MB, see
# .gitignore). The level-combat and story archives are not committed, so they
# are prefetched below.
COPY data/ ./data/
COPY python/scripts/ ./python/scripts/

# Volume mount-points used when PRTS_MCP_ROOT=/app (see prts_mcp/config.py).
RUN mkdir -p /data/gamedata /data/gamedata-levels /data/storyjson /data/images \
 && chown -R prts:prts /data

# --- Build-time prefetch (best effort) ------------------------------------
# Bakes the level-combat tree and the story zip into the image so a hosted
# container is fully functional with no outbound network at runtime. Failures
# are deliberately non-fatal: the container still starts, serves the operator
# tools from bundled data, and auto-sync retries in the background.
ARG PREFETCH_DATA=1
RUN if [ "$PREFETCH_DATA" = "1" ]; then \
        cd /app/python \
        && (python scripts/fetch_gamedata.py || echo "WARN: excel/levels prefetch failed") \
        && (python scripts/fetch_storyjson.py || echo "WARN: story prefetch failed"); \
    else \
        echo "PREFETCH_DATA=0: skipping build-time prefetch (runtime auto-sync only)"; \
    fi

USER prts

# Only meaningful with PRTS_TRANSPORT=http: Streamable HTTP on /mcp, probe on /health.
EXPOSE 3000

ENTRYPOINT ["prts-mcp"]

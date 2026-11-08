# =============================================================================
# pewpew Gallery — production image
#   1. python-builder — dependency venv and the pewpew package via uv
#   2. runtime        — slim, non-root, the `studio` CLI that serves the Gallery
# The page is the Console's committed build, package data inside pewpew
# (src/pewpew/sinks/web), so the image needs no Node stage. The server serves
# it from its own origin, so one container is the whole app: the page's
# relative /ws path works with no production-only configuration.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Python dependencies and the pewpew package
# ---------------------------------------------------------------------------
# Keep this tag in step with uv.lock. uv refuses a lock whose schema is newer
# than it understands, and a stale tag fails `uv sync --locked` here at deploy
# time.
FROM ghcr.io/astral-sh/uv:0.13-python3.14-trixie-slim AS python-builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Dependencies first, so a source-only change reuses this layer. The project is
# installed non-editable below, so the runtime venv carries the package itself
# and needs no source tree.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra studio --no-install-project --no-editable

COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra studio --no-editable

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.14-slim-trixie AS runtime

LABEL org.opencontainers.image.source="https://github.com/w-ash/pewpew" \
      org.opencontainers.image.description="pewpew Gallery: shared LED layouts, live in 3D"

RUN groupadd --gid 1000 pewpew && \
    useradd --uid 1000 --gid pewpew --create-home pewpew && \
    mkdir -p /app/data && chown pewpew:pewpew /app/data

# Root-owned, so the server process cannot rewrite its own code or the page it
# serves.
COPY --from=python-builder /app/.venv /app/.venv
# The example looks: the default share and every older bare-arrangement share open with them.
COPY examples/*.look.json /app/examples/

# The package is installed into .venv, so app.py's default examples path
# (three levels above the package file) points inside the venv. This override
# names the copy above instead.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PEWPEW_STUDIO_EXAMPLES=/app/examples

USER pewpew
# The one directory the runtime user can write. Without DATABASE_URL the CLI's
# SQLite fallback (./studio.sqlite3) is created here.
WORKDIR /app/data
EXPOSE 8000

# Fly uses its own check; this one reports status under plain `docker run`.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"]

# The CLI, not `uvicorn --factory`: it sets uvicorn's ws_max_size (256 KiB, the
# same cap the app enforces on bodies) and timeout_graceful_shutdown=30. Without
# those, uvicorn falls back to its own defaults.
#
# On SIGTERM uvicorn closes each session websocket with code 1012, so a deploy
# does not wait on open sessions. The 30s bound caps only a handler that does not
# finish; it stays under fly.toml's kill_timeout (60s).
CMD ["python", "-m", "pewpew", "studio", "--host", "0.0.0.0", "--port", "8000"]

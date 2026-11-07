# WS6 simplify pass

Scope: whole files `Dockerfile`, `.dockerignore`, `fly.toml`, `.github/workflows/release.yml`, `docs/deployment.md` (no diff).
Review ran inline (reuse, simplification, efficiency, altitude); the files were too small for separate agents.

## Changed
- `fly.toml:1-8`: removed the `[env]` block. Its only variable, `PYTHONUNBUFFERED=1`, is already set in `Dockerfile:83`. The `DATABASE_URL` comment moved to the file header. Wrapped the over-long first line.
- `.github/workflows/release.yml:19-21`: `TAG` is now set once at job level; it was repeated in two steps' `env`.
- `.github/workflows/release.yml:7`, deploy job (~line 49): dropped the job-level `permissions: contents: read`, which repeats the workflow-level default (line 9). Comment reworded to match.
- `docs/deployment.md:53-54`: the manual-deploy block repeated the commands from "First-time Fly setup" (lines 37-38); it now points there.

## Left alone
- `Dockerfile` two-step `uv sync` and the separate manifest `COPY` in the node stage: dependency-layer caching.
- `Dockerfile` `chown /app`: the SQLite fallback needs a writable working directory.
- `Dockerfile` HEALTHCHECK alongside Fly's check: `docker run` has no other health status, and `/health/live` skips the database.
- `.dockerignore`: dir/dir/** pairs are required by its stated matching rule; it stays an allowlist.
- `release.yml` `fetch-depth: 0`: probably unneeded (inference: only `CHANGELOG.md` is read), but I did not test it and it is behaviour-adjacent.
- Actions stay SHA-pinned; `fly.toml` `--ha=false` and single-machine comments are load-bearing.

Verification: `docker build` ok; no-`DATABASE_URL` run, 16 of 16 smoke checks passed, `id` uid=1000(pewpew), health status `healthy`.

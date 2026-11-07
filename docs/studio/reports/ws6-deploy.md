# ws6 deploy report

## What was written

- `Dockerfile`: three stages (uv builder, pnpm builder, slim runtime), the shape of the reference app (another of the maintainer's fly.io apps). CMD is `python -m pewpew studio --host 0.0.0.0 --port 8000`.
- `.dockerignore`: allowlist, mirroring the reference app.
- `fly.toml`: `app = 'pewpew-studio'`, `sjc`, and the settings from the brief.
- `.github/workflows/release.yml`: the reference app's workflow with pewpew wording. Only the deploy comment changed.
- `docs/deployment.md`: the reference app's shape, adapted to the studio.

## Deviations from the reference app

- **Two-step `uv sync`.** The first step installs dependencies with `--no-install-project --no-editable`, and the second installs the project after `src/` is copied. This is the pattern in the uv Docker guide, which I checked. It keeps the dependency layer cached.
- **No `src/` in the runtime stage.** The package is non-editable, so it lives in `/app/.venv`. The reference app copies `src/` because its path anchor needs it. pewpew does not.
- **`PEWPEW_STUDIO_WEB_DIST=/app/web/dist`.** `studio/app.py` finds `web/dist` three levels above the package file. In a non-editable install that resolves inside the venv, so the SPA would not mount. The env override already exists in `app.py`, and the Dockerfile sets it.
- **`chown pewpew /app`.** Without `DATABASE_URL`, the server writes `./studio.sqlite3` in `/app`. That directory is root-owned by default, so the local test in `docs/deployment.md` would fail without this.
- **`web/e2e` stays in the build context.** `web/tsconfig.json` includes `e2e`, and `pnpm build` runs `tsc`. The reference app excludes its e2e tree because its tsconfig includes only `src`.
- **User and label names.** The runtime user is `pewpew`, not the reference app's name. The image label points at `https://github.com/w-ash/pewpew`, taken from the repo's origin remote.
- **`[env]` is only `PYTHONUNBUFFERED`.** The reference app's `LOGGING__*`, `AUTH__*` and `CORS_ORIGINS` have no pewpew counterpart in the code I read.
- **No `release_command`, no migrations.** pewpew creates its table at startup.
- **Health path** is `/health/live`, not `/api/v1/health/live`.
- **`HEALTHCHECK` start period** is 60s, copied from the reference app. I did not measure startup time.

## Verification

- `docker build -t pewpew-studio:local .` did not run. The Docker daemon is unreachable (`~/.orbstack/run/docker.sock` is missing). Nothing was built.
- Paths the Dockerfile copies, checked against the worktrees:
  - `pyproject.toml` and `uv.lock`: present in ws6 but without the `studio` extra. Present with it in ws3-simplify.
  - `src/`: ws3-simplify has `src/pewpew/studio/`, which only exists after the merge.
  - `web/package.json`, `web/pnpm-lock.yaml`, `web/pnpm-workspace.yaml`, `web/`: present in ws4-web only.
- Paths that only exist after the merge: `src/pewpew/studio/`, the `studio` extra in `uv.lock`, and the whole `web/` tree.

## Checks after the merge

1. Merge ws3-simplify and ws4-web into this branch, then re-run the docker build.
2. Confirm `uv.lock` has the `studio` extra. `uv sync --locked` fails otherwise.
3. Confirm the `uv` image tag `0.13-python3.14-trixie-slim` can read the merged `uv.lock` (revision 5 in ws3).
4. Confirm `pnpm build` passes with `web/e2e` present. `tsc` type-checks it.
5. Confirm `web/dist` lands at `/app/web/dist` and that `/` returns `index.html` in the local run.
6. Confirm `/health/live` returns `{"ok": true}` in the local run without `DATABASE_URL`.
7. Before the first deploy: confirm the Neon region against `primary_region = 'sjc'`, and confirm the app name at `fly launch`.
8. Before tagging: add a `## [x.y.z]` section to `CHANGELOG.md`, or `release.yml` fails.

Nothing was deployed. No `fly` command was run.

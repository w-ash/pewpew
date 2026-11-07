# Code review of the ws6 deploy section (high effort)

- **Reviewer:** an independent agent (Opus), not the author. It ran the `code-review` skill at
  high effort, checked each skill finding against `66729ee`, merged four into others, and dropped
  one candidate of its own that it could not back up (the `.dockerignore` header's claim about
  directory rules).
- **Target:** `Dockerfile`, `.dockerignore`, `fly.toml`, `.github/workflows/release.yml` and
  `docs/deployment.md` at `66729ee`, on 2026-10-22. Line numbers refer to that commit.
- **Verdict:** the image, health checks, single-machine deploy and shutdown hold. Two medium
  gaps: a tag deploys with no test run, and secrets inside `src/` or `web/` can enter the build.
- **Fixes:** the fix pass records what it did with each finding in `ws6-fixes.md`.

## Findings, most severe first

**1. A tag deploys code that nothing has tested.** CONFIRMED, medium
- **Where:** `.github/workflows/release.yml:3-5, 48-64`. At `66729ee`, `.github/` holds only
  this file.
- **Defect:** no job runs `uv run pytest`, `pnpm build` or a Docker build before
  `flyctl deploy`. Nothing checks that the tagged commit is on `main`. The Release is published
  (`:42-46`) before the image is first built.
- **Scenario:** a commit with a failing golden test is tagged. It goes live, because the only
  check is `/health/live` (`src/pewpew/studio/app.py:316-318`), which passes even when
  `/api/compile` is broken. If the Docker build fails instead, a public Release points at code
  that never deployed.
- **Fix:** add a test job that `release` needs: `uv sync --locked`, `uv run pytest`,
  `pnpm install --frozen-lockfile && pnpm build`, and a Docker build. The reference app (another of
  the maintainer's fly.io apps) has these in its `.github/workflows/ci.yml`. Optionally, check
  `git merge-base --is-ancestor "$GITHUB_SHA" origin/main`.

**2. Secrets and databases inside `src/` or `web/` enter the build, and `src/` ones the image.**
CONFIRMED, medium
- **Where:** `.dockerignore:10-15`. Nothing after the `!src/**` and `!web/**` re-includes
  excludes them again (`:17-35`).
- **Defect:**
  - A build of `66729ee`'s `.dockerignore` over decoy files sent `src/pewpew/.env`,
    `src/pewpew/key.pem`, `src/pewpew/studio/studio.sqlite3`, `web/.env`,
    `web/.env.production.local`, `web/server.key` and `web/local.db`.
  - It also sent `web/.eslintcache`, `web/.vite/` and `web/tsconfig.tsbuildinfo`.
  - Root-level copies stayed out.
  - The build context has no `.gitignore`, so hatchling cannot filter by it. A wheel built from
    `66729ee`'s `pyproject.toml` and `src/` with no `.gitignore` packaged
    `pewpew/.env`, `pewpew/key.pem` and `pewpew/studio/studio.sqlite3`.
  - `uv sync --no-editable` (`Dockerfile:34`) installs that wheel into the venv that the runtime
    stage copies (`:75`).
- **Scenario:**
  - A local `web/.env.production.local` with a `VITE_*` key is loaded by `vite build`
    (<https://vite.dev/guide/env-and-mode>), and Vite writes the value into the public bundle.
  - `web/.gitignore` ignores `*.local`, but `!web/**` adds the file back.
  - The documented manual deploys (`docs/deployment.md:37, 56`) build from the developer's own
    tree.
- **Fix:** after the re-includes, add `**/.env*`, `**/*.local`, `**/*.pem`, `**/*.key`,
  `**/*.sqlite3*`, `**/*.db`, `**/.pytest_cache`, `web/.vite`, `web/*.tsbuildinfo` and
  `web/.eslintcache`. The reference app's `.dockerignore` has the same gap.

**3. Fly's connection cap sits just above the app's session cap.** PLAUSIBLE, medium
- **Where:** `fly.toml:36-39`, with `src/pewpew/studio/limits.py:21` (`MAX_SESSIONS = 20`).
- **Defect:**
  - Fly's docs (<https://docs.fly.io/reference/configuration>) say what these settings do:
    - `type = 'connections'` counts concurrent TCP connections.
    - At `hard_limit` the proxy "will stop sending new traffic to that Machine".
  - When every machine is at the limit, Fly queues new traffic and "might start returning 503"
    (<https://docs.fly.io/reference/load-balancing>).
  - A hidden tab pauses its session but keeps its socket open
    (`web/src/session/client.ts:101`).
- **Scenario:**
  - 20 open sessions, background tabs among them, leave 5 connections for every page load,
    asset, catalog, GLB and new websocket.
  - New visitors wait or get a 503 from the proxy. They never reach the app's eviction of
    paused sessions (`app.py:386`) or its own refusal message.
  - Not verified: how many backend connections one page load uses.
- **Fix:** raise `hard_limit` well above `MAX_SESSIONS` plus HTTP headroom, or use
  `type = 'requests'` with such a limit. The values came from the reference app (its
  `fly.toml`), which serves two users.

**4. A multi-tag push can deploy in parallel, or not at all.** CONFIRMED, low
- **Where:** `.github/workflows/release.yml` (no `concurrency:`), `docs/deployment.md:50`.
- **Defect:** `git push origin main --tags` pushes every local tag. GitHub creates no tag
  events "when more than three tags are pushed at once"
  (<https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>).
  With two tags, two `flyctl deploy` runs race, and whichever finishes last stays live, possibly
  the older tag.
- **Fix:** add `concurrency: {group: fly-deploy, cancel-in-progress: false}` to the deploy job,
  and document `git push origin main v0.1.0`.

**5. The shutdown comments and docs misdescribe uvicorn.** CONFIRMED, low
- **Where:**
  - `Dockerfile:97-100`: "an open session websocket never ends on its own".
  - `docs/deployment.md:88-91`: "pauses for up to 30 seconds".
  - `fly.toml:12-14`: SIGTERM "so the CLI's uvicorn runs its graceful shutdown".
- **Defect:**
  - uvicorn 0.54 (`uv.lock:874-875`) chooses `WebSocketsSansIOProtocol` when `websockets` is
    installed (`uvicorn/protocols/websockets/auto.py`).
  - Its `shutdown()` sends a 1012 close and queues a disconnect to the app
    (`websockets_sansio_impl.py:177-192`).
  - SIGINT is handled the same as SIGTERM (`uvicorn/server.py:45-48, 351-356`).
- **Evidence:**
  - Running `66729ee`'s CLI with a session open, SIGTERM exited in 0.17 s and SIGINT in 0.26 s.
    In both runs the client saw close code 1012.
  - `docs/studio/reports/ws3-server.md:3` measured 0.03 s.
  - The wording came from the reference app (its `Dockerfile`), where it holds for an SSE
    response.
- **Fix:** say that uvicorn closes session sockets with 1012, so a deploy does not wait, and
  that the 30 s bound only caps a stuck handler. Keep SIGTERM, but drop the claim that SIGINT
  skips the graceful shutdown.

**6. `fly launch` may rewrite the committed `fly.toml`.** PLAUSIBLE, low
- **Where:** `docs/deployment.md:21`, which says it "keeps the committed fly.toml".
- **Defect:** flyctl's docs (<https://docs.fly.io/flyctl/launch/>) list `--copy-config` ("Use
  the configuration file if present without prompting") and say `--path` is "where fly.toml file
  will be saved". Whether it reserializes the file and drops the comments is not verified
  (inference).
- **Fix:** use `fly apps create pewpew`, which creates the app without touching `fly.toml`.

**7. The runtime user owns its own code.** CONFIRMED, low
- **Where:** `Dockerfile:73-77`.
- **Defect:** `chown pewpew /app`, and `--chown=pewpew:pewpew` on the venv and `web/dist`, let
  the server process rewrite its installed package and the SPA it serves. Ownership of `/app`
  alone is enough to rename `.venv`.
- **Scenario:** a path-write or code-execution bug survives as modified code until the next
  deploy.
- **Fix:** copy the venv and `dist` as root, and give the SQLite fallback its own writable
  directory (`/app/data`, with `--db /app/data/studio.sqlite3`). The reference app does the
  same (its `Dockerfile`), so this is parity, not a regression.

**8. Two build inputs float.** CONFIRMED, low
- **Where:** `release.yml:59`, and `Dockerfile:17, 39, 62`.
- **Defect:**
  - `setup-flyctl` at `ed8efb3` defaults `version` to `latest` (its `action.yml`), so the SHA
    pin does not pin the flyctl binary.
  - The three base images are tags without digests, the same tags as the reference app.
- **Fix:** set `with: version: <x.y.z>`, and pin the base images with `@sha256:` digests.

**9. The release checkout fetches full history.** CONFIRMED, nit
- **Where:** `release.yml:25-26`.
- **Defect:** `fetch-depth: 0` is not needed. The job only reads `CHANGELOG.md` and tags an
  existing ref.
- **Fix:** delete it.

**10. Nothing ties the tag to the package version.** CONFIRMED, nit
- **Where:** `pyproject.toml:3` (`0.0.1`), `web/package.json:4` (`0.1.0`), and
  `docs/deployment.md:50` (`v0.1.0`).
- **Fix:** have the release job fail when `${TAG#v}` differs from `pyproject.toml`'s version.

## Checked and holding

- **Non-root:** uid/gid 1000 `pewpew`, with `USER pewpew` before `CMD` (`Dockerfile:67-68, 86`).
  The local `pewpew:local` image reports `User=pewpew`. That image may have been rebuilt from
  the working tree, so it is supporting evidence only.
- **No baked secrets:**
  - The Dockerfile has no `ARG`, and its `ENV`s are `UV_*`, `PATH`, `PYTHONUNBUFFERED` and
    `PEWPEW_STUDIO_WEB_DIST` (`:21-23, 82-84`).
  - `DATABASE_URL` comes only from `fly secrets set` (`fly.toml:23-24`, `docs/deployment.md:28`).
  - The runtime stage copies only the venv and `web/dist` (`:75, 77`). Finding 2 is the
    exception.
  - `docker history` shows no secret in the project's layers.
- **`.dockerignore` at root:** the probe kept root `.env*`, keys, `*.sqlite3`, `*.db`, `.venv`,
  `.claude/`, `research/clones/`, `web/node_modules` and `web/dist` out. `web/e2e` stays in on
  purpose, because `web/tsconfig.json` includes it.
- **Workflow pins and permissions:**
  - The two action SHAs match `actions/checkout` v7.0.1 and `superfly/flyctl-actions` 1.6
    (GitHub API).
  - The workflow default is `contents: read`. Only the release job gets `write`
    (`release.yml:9-10, 20-21, 53-54`).
  - The tag reaches the shell through `env`, not by interpolation (`:39-40, 44-46`).
- **CMD:** `Dockerfile:101` is exactly the launch line in `docs/studio/contracts.md:75-77`.
- **Health checks:** Docker (`Dockerfile:90-91`) and Fly (`fly.toml:43-48`) both probe
  `/health/live`, which returns a constant (`app.py:316-318`). The database is touched only at
  startup (`app.py:278-279`).
- **One machine:**
  - `--ha=false` appears in the workflow (`release.yml:64`) and in every documented deploy
    (`docs/deployment.md:37, 47, 56, 60`).
  - `fly.toml:32-34` sets `auto_stop_machines = 'off'` and `min_machines_running = 1`.
  - The docs and the workflow agree.
- **Shutdown inside `kill_timeout`:** `fly.toml:15-16` sets SIGTERM and 60 s.
  - The worst case is 30 s of graceful drain (`src/pewpew/__main__.py:364`), then lifespan
    shutdown (`app.py:280-285`).
  - Lifespan shutdown joins the session threads within a 5 s deadline
    (`src/pewpew/studio/session.py:352-360`). The threads are daemons (`:115`).
  - Measured: 0.17 s with a session open.
- **Docs facts:**
  - The Vite proxy is on 5173 (`web/vite.config.ts:31-36`).
  - A hidden tab pauses its session (`web/src/session/client.ts:101`).
  - `CHANGELOG.md` has only `[Unreleased]` (`:8`).
  - `PEWPEW_STUDIO_WEB_DIST` is read at `app.py:426`.
- **Parity with the reference app:**
  - These match: the base image tags, the pnpm pin, the user setup, the `HEALTHCHECK` shape,
    the Fly checks, the kill settings, the VM, the concurrency numbers and the
    tag → Release → deploy flow.
  - Deliberate differences: pewpew SHA-pins its actions where the reference app uses tags, and scopes
    `contents: write` to one job where the reference app grants it workflow-wide.
  - pewpew runs the contract CLI instead of bare uvicorn, so it has no `--limit-concurrency 50`.
  - pewpew installs its package non-editable instead of copying `src/`.
  - The one gap is that pewpew has no CI workflow (finding 1).

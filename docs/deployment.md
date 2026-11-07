# Running and deploying the pewpew studio

The studio is one container: the CLI serves the API, the render websockets and
the built frontend from the same origin, backed by Neon PostgreSQL when
`DATABASE_URL` is set. This page deploys your own instance; the names below
are the examples in the committed `fly.toml`.

- **Platform**: Fly.io, one machine (`primary_region`, for example `sjc`)
- **App name**: for example `pewpew`, at `https://<app>.fly.dev`; Fly app
  names are global, so pick a free one and set it in `fly.toml`
- **Database**: Neon Postgres, via `DATABASE_URL`

## Local development

Not covered here. Run the server with `python -m pewpew studio` (SQLite at
`./studio.sqlite3`) and the frontend with `pnpm dev` in `studio-web/`. Vite on 5173
proxies `/api` and `/ws` to port 8000.

## First-time Fly setup

```bash
fly auth login
fly apps create <app>    # creates the app and leaves the committed fly.toml alone
```

Set the secret **before the first deploy**, so the first machine never writes to
the SQLite fallback:

```bash
fly secrets set DATABASE_URL='postgresql://USER:PASS@HOST/DB?sslmode=require'
```

The URL uses the plain `postgresql://` scheme. The store connects with psycopg 3,
which takes that form directly.

Then:

```bash
fly deploy --ha=false
fly scale count 1     # assert a single machine; see below
```

Every `fly secrets set` restarts the machine. Batch secrets into one command.

## Deploying

Tagging is the deploy. `.github/workflows/release.yml` fires on a `v*` tag. It
runs the Python and web tests and a Docker build, checks that the tag matches
`pyproject.toml`'s `version` and that `CHANGELOG.md` has that version's section,
publishes a GitHub Release, then runs `flyctl deploy --remote-only --ha=false`.
Deploys run one at a time.

Push the one tag by name. `--tags` pushes every local tag, and GitHub starts no
workflow at all when more than three tags arrive in one push
(<https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>).

```bash
git tag v0.1.0 && git push origin main v0.1.0
```

pewpew has no tags yet, so the first deploys are manual (`fly deploy --ha=false`,
as in First-time Fly setup).

Always pass `--ha=false`. Fly otherwise provisions a second machine for high
availability, which this app cannot have (see below).

## Why exactly one machine

Not a cost decision. The studio keeps its live state in memory:

- each visitor's render session runs on its own thread inside the process;
- the admission limits and rate limits are in-memory counters.

A second machine would split these, so one visitor's session and limits would
not match what another machine sees. `auto_stop_machines = 'off'` keeps Fly's
proxy from stopping the machine, and `--ha=false` on every deploy stops Fly
adding one. Verify with `fly status` after any deploy: the Machines table must
have exactly one row.

## Health checks

| Endpoint | Queries the DB | Used by |
|---|---|---|
| `/health/live` | no | the Fly health check and the Docker `HEALTHCHECK` |

The platform probe must not touch the database. A probe every 30 seconds would
keep a Neon compute out of autosuspend, and a brief database outage would fail
the machine's health check.

## Deploy characteristics

- **A deploy does not wait on open sessions.** On SIGTERM uvicorn closes each
  session websocket with code 1012, and the page reconnects to the new machine.
  `python -m pewpew studio` sets `timeout_graceful_shutdown=30`, which caps only
  a handler that does not finish. It stays under Fly's 60s `kill_timeout`.
- **Logs are stdout only** (`fly logs`).

## Costs

Fly egress is $0.02/GB (<https://docs.fly.io/about/pricing>). Every frame is
streamed to the browser, so the page pauses frames while its tab is hidden
(`pause` and `resume` messages). A background tab then sends no frames.

## Testing the production image locally

Build and run what Fly builds, without `DATABASE_URL`, so the SQLite fallback
serves the app:

```bash
docker build -t pewpew:local .
docker run --rm -p 8080:8000 pewpew:local
```

Then check: `http://localhost:8080/health/live` answers `{"ok": true}`, and `/`
returns the SPA's `index.html`. The SQLite fallback writes
`/app/data/studio.sqlite3`, the only directory the runtime user can write.

## Release notes

`release.yml` needs `pyproject.toml`'s `version` to equal the tag without its
`v`, and a `## [x.y.z]` section in `CHANGELOG.md` for it. The current CHANGELOG
has only `[Unreleased]` and the version is `0.0.1`, so the first tag needs both
set first.

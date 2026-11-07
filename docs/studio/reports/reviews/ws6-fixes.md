# ws6 review fixes

Fixes for [`ws6-code-review.md`](ws6-code-review.md) (10 findings), on `studio` after the simplify
pass ([`ws6-simplify.md`](ws6-simplify.md)). The review's line numbers are at `66729ee`.

## Per finding

1. **Fixed.** `release.yml` has a `test` job that `release` needs: `uv sync --locked`, `uv run
   pytest`, `pnpm check` and `pnpm test`, and a `docker build .`. The new actions are SHA-pinned:
   `astral-sh/setup-uv` v10.3.0, `pnpm/action-setup` v6.1.0 and `actions/setup-node` v7.1.0, with
   SHAs read from each tag through the GitHub API. `actionlint` 1.7.12 passes. **Skipped:** the
   optional check that the tag is on `main`. It needs full history, and every tag so far is cut
   from `main` by one person.
2. **Fixed.** `.dockerignore` re-excludes `**/.env*`, `**/*.local`, `**/*.pem`, `**/*.key`,
   `**/*.sqlite3*`, `**/*.db`, `**/.pytest_cache`, `web/.vite`, `web/*.tsbuildinfo` and
   `web/.eslintcache` after the re-includes. A context probe over decoys of each kind, in `src/`,
   `web/` and the root, sent none of them and kept `pyproject.toml`, `uv.lock`, `src/`,
   `web/src/`, `web/e2e/` and `web/package.json`.
3. **Fixed.** `fly.toml` raises the connection cap to `hard_limit = 100` and `soft_limit = 80`,
   well above the app's 20 sessions, with a comment saying why. The values are a judgement, not a
   measurement; the project's list of open decisions, not in this repo, lists them.
4. **Fixed.** The deploy job has `concurrency: {group: fly-deploy, cancel-in-progress: false}`,
   and `docs/deployment.md` pushes one tag by name and says why.
5. **Fixed.** The Dockerfile, `fly.toml` and `docs/deployment.md` now say that uvicorn closes
   session websockets with 1012 on SIGTERM, that the 30 s bound caps only a stuck handler, and
   that SIGINT is graceful too. uvicorn 0.54.0 handles both signals in `handle_exit`
   (`uvicorn/server.py:45-47, 351-356`), and its sans-I/O websocket `shutdown()` sends 1012
   (`uvicorn/protocols/websockets/websockets_sansio_impl.py:177-192`). Measured on the fixed image
   with a bound session: the socket closed 0.29 s after `docker stop`, with code 1012, and the
   container stopped in 0.57 s.
6. **Fixed.** First-time setup uses `fly apps create pewpew`, which "won't generate a fly.toml"
   (<https://fly.io/docs/flyctl/apps-create/>).
7. **Fixed.** The runtime stage copies the venv and `web/dist` as root. `/app/data` is the only
   directory `pewpew` owns, and the final `WORKDIR`, so the CLI's default `./studio.sqlite3` lands
   there and the CMD stays as pinned. In the container, writes to `/app/.venv` and `/app/web/dist`
   fail with "Permission denied", and the fallback database is `/app/data/studio.sqlite3`.
8. **Partly fixed.** `setup-flyctl` installs flyctl `0.4.114` (released 2026-10-07). **Skipped:**
   digest pins for the three base images. A digest stops Debian and Python patch releases from
   reaching the next deploy until someone bumps it, and the tags already pin uv 0.13, Python 3.14
   and Node 24, as the reference app does. The project's list of open decisions, not in this
   repo, lists it.
9. **Fixed.** The release checkout no longer sets `fetch-depth: 0`.
10. **Fixed.** The release job fails when the tag without its `v` differs from `pyproject.toml`'s
    `version` (now `0.0.1`). `docs/deployment.md` says so.

## Checks

- `docker build -t pewpew:local .` succeeds. With no `DATABASE_URL`, the container runs as uid
  1000 `pewpew` and the smoke test passes 16 of 16 checks, including live `power` messages and
  the golden-rings report (2 boards, 6 chains, 24 feeds, 5 PSUs, 1,228.8 W). The Report panel
  shows the totals with no page errors.
- Gates: `uv run --all-extras --all-groups pytest`, and `pnpm check`, `pnpm test` and `pnpm e2e`
  in `web/`, all pass.

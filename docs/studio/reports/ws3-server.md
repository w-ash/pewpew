# ws3: studio backend

Built `src/pewpew/studio/`, the `studio` CLI subcommand and `scripts/export_openapi.py`. All of contracts.md's HTTP routes and `/ws/session` exist. `uv run pytest` passes (268 passed, 2 xfailed, about 3.6 s). A real `python -m pewpew studio` run served frames (200 bytes = 8 + 3·64) and shut down 0.03 s after SIGTERM with the socket open. Nothing was run against a live Postgres.

## What is where

| File | Contents |
|---|---|
| `src/pewpew/studio/app.py` | `create_app(*, catalog, compile, store, build_glb, assembly_digest, web_dist, limits, fps, idle_timeout_s)`, routes, websocket handler, SPA mount |
| `src/pewpew/studio/session.py` | `Session` (Renderer + PacedLoop thread), `SessionRegistry` |
| `src/pewpew/studio/transport.py` | `Outbox`: one-slot newest-wins frame mailbox, bounded ordered control queue, sender |
| `src/pewpew/studio/limits.py` | `Limits`, `Admission`, `SaveLimiter`, `BodyLimit` middleware, `client_ip` |
| `src/pewpew/studio/store.py` | canonical JSON, content id, `SqliteStore`, `PostgresStore` |
| `src/pewpew/controls.py` | `LoopControls`, moved out of `__main__.py`; `_LoopControls` is still importable from there |
| `tests/test_studio.py` | 28 tests with a fake rig |

## Decisions

- **Postgres: sync psycopg 3, one short connection per call, from FastAPI's threadpool.** Routes are plain `def`, so it needs no second async code path, and SQLite shares the same `Store` interface. A fresh connection each time survives Neon's idle autosuspend; saves are capped at 10 a minute per address, so the connect cost is small. `PostgresStore` is untested against a server.
- **Pause stops the `PacedLoop`** and the thread waits, instead of rendering and discarding frames. `run()` is resume-safe and keeps engine time (`src/pewpew/pace.py:116-120`).
- **Idle pause:** after 10 minutes with no inbound message the session pauses, and any later message other than `pause` resumes it. Contracts say only "pauses"; without this a visible, idle tab would stay frozen.
- **Failure containment.** Each queued closure catches its own errors, since an exception from `call_soon` ends `run()` (`src/pewpew/pace.py:103-114`). A bind whose `setup` raises restores the old mapping and sends `refused`. If even that fails, the thread ends and the socket closes.
- **Canonical JSON** is the submitted arrangement, not the migrated one, with `allow_nan=False`. Text is stored as `TEXT`, not `jsonb`, so the hashed bytes survive a round trip.
- **Save compiles first** and refuses an arrangement that does not compile (422), so stored links are loadable.
- **Pattern names** are lowercase class names from `pewpew.patterns.__all__`, the `pewpew.load` rule (`src/pewpew/load.py:236-241`). `rainbow` appears when ws5 adds it to `__all__`; until then the default is `plasma`.
- **Websocket refusals** (socket or session cap) are sent as a `refused` message with `name: "session"`, then close 1013, because a close before accept would give the browser no reason.
- `/api/arrangements/{id}` replies carry `Cache-Control: ... immutable` (content-addressed).

## Deviations from or gaps in contracts.md

1. **Catalog shape is assumed.** contracts.md gives no `Catalog` serialization. `/api/catalog` calls `catalog.to_json()` and expects `{"digest", "fixture_types": [{id, name, ...}], "attachment_types": [...], "controllers", "psus", "cables", "presets"}`. It adds `digest` and `assembly_url` to each fixture and attachment type. ws1 needs to supply `Catalog.to_json()` in that shape, or tell me the real one.
2. **Initial binding.** The contract has `hello` on connect but no initial rig, so a session starts on `line(64)` until the first `bind`. `hello.n` is 64 at first.
3. **Extra fields.** `refused` for a failed bind carries `name: "bind"`, `reason` and `issues`. A `pattern` refusal has `name: "pattern"`.
4. **422 from `/api/compile` and save** is `{"issues": [...]}`, not FastAPI's `detail` wrapper. A non-object body gets FastAPI's own 422 with `detail`.
5. **Limits not in the contract:** 429 with `Retry-After` for saves; 413 for bodies; unknown path 404 for non-API misses in the SPA.
6. **`create_app` takes `fps`, `idle_timeout_s`, `limits`** so tests run fast; defaults are 30, 600 s and the spec limits.
7. **pyproject:** the `studio` extra is as specified (floors match the maintainer's other fly.io apps: fastapi 0.143, uvicorn 0.54, psycopg 3.3). I also added `httpx2` to `dev` (Starlette's TestClient warns that `httpx` is deprecated) and a `dev` dependency group, `pewpew[dev,studio]`, because `uv run` does not install extras and the studio tests would otherwise skip. I did not add pydantic to core: fastapi brings it, and ws1 owns that change. ws1 and I will both touch `pyproject.toml`; expect a trivial merge.

## Open issues

- **Group size is unbounded before compile.** The 200-fixture limit is checked on an explicit `fixtures` list before compiling, and on `rig.fixtures` after. A `ring` preset with a huge count would be expanded by `compile_rig` first. ws1 should cap group sizes inside compile.
- **No pixel cap.** 200 long tubes could make large frames (n·3 bytes at 30 fps). Not in the spec; consider a cap on `rig.n`.
- **Compile and bind are not rate limited** beyond the 20-session and 3-per-address caps and 256 KiB bodies.
- **Websocket frame size is also enforced by uvicorn only if started with `ws_max_size=262144`.** The CLI does this. ws6's Dockerfile CMD must pass `--ws-max-size 262144` and `--timeout-graceful-shutdown 30` (another of the maintainer's fly.io apps does the latter in its CMD). The app also refuses oversize text after receipt.
- **`Fly-Client-IP` is spoofable off Fly.** Fly's page says the header is "the IP address of the client from the perspective of Fly Proxy" but does not say it overwrites a client-supplied value (https://docs.fly.io/networking/request-headers); I did not confirm that. Behind Fly it is the intended key.
- **Power:** the session reads `rig.report.estimate_effect_power` if present; tested with a fake only.
- **Bind or pattern changes while paused** apply on resume.
- The default `compile`, `load_catalog`, `build_glb` and `assembly_digest` import `pewpew.rig` on first use; none has run against the real rig.
- `/health/live` is the only health route; the reference app's extra `/health` (database mode) is not ported.

## Sources

- Preview protocol and trust comments: `src/pewpew/sinks/preview.py:8-45`, `src/pewpew/sinks/base.py:61-75`.
- Loop and renderer semantics: `src/pewpew/pace.py:55-186`, `src/pewpew/render.py:130-140` (`rebind` keeps `t`), `src/pewpew/render.py:195-240` (`swap`).
- Couplefins patterns followed: `src/interface/api/app.py` (static mount, `generate_unique_id_function`), `src/interface/api/rate_limit.py`, `src/interface/api/routes/health.py`, `scripts/export_openapi.py`, `Dockerfile:90-110`, `pyproject.toml`.
- Fly header: https://docs.fly.io/networking/request-headers

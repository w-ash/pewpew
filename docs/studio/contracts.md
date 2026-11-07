# Studio interface contracts

These are the seams between workstreams. The design behind them is in
[`domain-model.md`](domain-model.md), and the plan is in [`plan.md`](plan.md). A workstream that
needs to change a contract says so in its report rather than changing it on its own.

## Layout and owners

| Path | Owner |
|---|---|
| `src/pewpew/rig/`: `models.py`, `expr.py`, `catalog.py`, `data/<kind>/*.json`, `pose.py`, `presets.py`, `compile.py`, `migrate.py`, `__init__.py` | ws1 |
| `src/pewpew/rig/geometry.py` | ws1b |
| `src/pewpew/rig/wiring.py`, `src/pewpew/rig/electrical.py` | ws2 |
| `schemas/arrangement.v1.json`, `schemas/catalog.v1.json` (generated, committed) | ws1 |
| `examples/*.look.json` (the studio's example looks) | ws5 |
| `src/pewpew/studio/` (FastAPI app, sessions, store, limits) and `python -m pewpew studio` | ws3 |
| `studio-web/` (Vite + React + R3F) | ws4 |
| `Dockerfile`, `.dockerignore`, `fly.toml`, `.github/workflows/release.yml`, `docs/deployment.md` | ws6 |
| `research/` ADRs and source fragments, `CHANGELOG.md` | ws7 |
| `docs/studio/reports/<workstream>.md` | each workstream writes its own |

Nobody edits `docs/backlog/` yet, because another session has uncommitted edits there. ws7 folds
the reports into the backlog later.

## Python API (ws1 owns; everyone else consumes)

```python
from pewpew.rig import (
    Arrangement, Catalog, CompiledRig, RigError,
    load_arrangement, load_catalog, compile_rig,
)

catalog: Catalog = load_catalog()           # bundled src/pewpew/rig/data, validated, cached
arr: Arrangement = load_arrangement(obj)    # dict | str (always JSON text) | os.PathLike (a file);
                                            # migrated to the latest version; strict types
rig: CompiledRig = compile_rig(arr, catalog)  # pure: no I/O, no clock, no RNG

rig.n                  # int, pixel count
rig.mapping            # (N,3) float32, Contain-normalized 0..1, read-only; goes to Renderer
rig.positions_m        # (N,3) float64, world meters
rig.normals            # (N,3) float64, zero rows for omnidirectional fixtures
rig.fixture_of         # (N,) int32, index into rig.fixtures
rig.pixel_in_fixture   # (N,) int32
rig.fixtures           # tuple[FixtureInstance]: id, type_id, matrix (16 floats, column-major,
                       #   three.js Matrix4.elements order), attachments {"end_a"|"end_b": id|None},
                       #   pixel_start, pixel_count (each fixture's pixels are contiguous, in data order)
rig.grouping           # pewpew.mapping.Grouping: each fixture as one unit, centred on the mean of its
                       #   pixels in rig.mapping; fixture_grouping(mapping, fixtures) builds it
rig.slices             # tuple[OutputSlice]: controller, output, start, count, led_type, color_order
rig.report             # RigReport | None; filled by ws2; pydantic, JSON-serializable
rig.issues             # tuple[Issue]: level ("error"|"violation"|"warning"), code, message, ref
rig.catalog_digest     # str, a content hash of the catalog
rig.to_json()          # dict without numpy: the body of POST /api/compile's response
```

- `RigError(ValueError)` carries `.issues`. It is raised for error-level issues; violations and
  warnings are returned on `rig.issues`.
- A look renders per pixel (ADR-025, `research/synthesis/decisions/ADR-025-one-effect-system.md`):
  the running look is rebound to `rig.mapping` and `rig.grouping` (`renderer.rebind(rig.mapping,
  rig.grouping)` on each layer's renderer). `index` follows data order because the pixels are
  compiled in that order.

**Pinned 2026-10-22 after ws1 and ws3 landed.**
- **`Catalog.to_json()`** (in `src/pewpew/rig/catalog.py`) returns
  `{"digest", "fixture_types", "attachment_types", "controllers", "psus", "cables", "presets"}`.
  Each numeric fact is `{"v", "status", "src"}`, plus `expr` when the value came from an
  expression. `/api/catalog` adds `digest` and `assembly_url` to each fixture and attachment type.
- **Effect power.** `CompiledRig.estimate_effect_power(frame_linear) -> float` takes the
  renderer's linear-light `(N,3)` float frame and returns watts. ws2 implements it, delegating to
  a pure function in `src/pewpew/rig/electrical.py`, and the studio session calls it. It is a
  method on `CompiledRig`, not on `report`.
- **`FixtureInstance` additions from ws1:** `group`, `controller`, `output`, `chain`, and
  `attachment_matrices`. Each attachment's world frame is 16 column-major floats. An attachment's
  local frame has its origin at the anchor, +y along the anchor's `dir`, and +z equal to the
  host's +z.
- **422 body.** Every 422 from the studio, including malformed JSON and non-object bodies, is
  `{"issues": [...]}`.
- **Launch.** Production runs `python -m pewpew studio --host 0.0.0.0 --port 8000`, which sets
  uvicorn's `ws_max_size=262144` and `timeout_graceful_shutdown=30`. Never run bare
  `uvicorn --factory`, which falls back to uvicorn's defaults.

**Pinned 2026-10-23 with the power cap** (`docs/studio/reports/power-cap.md`).
- **Arrangement `power`.** An optional block `{"max_watts": float | null, "max_brightness": float}`.
  `max_watts` is over 0 and at most 1e6, `max_brightness` is 0 to 1, and the default caps nothing.
  The format stays version 1, because a file without the block means what it meant before.
- **The limiter.** `pewpew.power.PowerLimiter` is the engine's stage-3 power limit (ADR-001
  amendment 2026-10-23). `rig.power_cap` is the arrangement's `PowerCap`, `rig.power` is the
  `pewpew.power.EffectPower` current model, and `rig.limiter(cap=None)` gives a limiter for the
  rig under `cap` or under `rig.power_cap`. A limiter call returns `Limited(frame, scale, watts,
  uncapped_watts)`.
- **Report.** `totals.worst_w`/`worst_a` have every channel full. `rgb_worst_w`/`rgb_worst_a`
  are the most the RGB stream draws through each board's auto-white (Accurate: 2 of an RGBW
  pixel's 4 channels). `capped_w`/`capped_a` are that under the cap; PSUs are sized for them, with
  or without a cap. Each PSU's `current_a`, `load_fraction` and `watts` are its capped load, and
  `worst_a` its every-channel load. Both include `board_a`: the boards the PSU `powers`, each
  board's `power_w` through a buck at `BUCK_EFFICIENCY` (assumed 70%). The totals and effect power
  count that draw as flat, so the cap never scales it and `max_watts` leaves room for it. Each feed's `current_a` has every channel full (the drop uses
  it), and `capped_a` is the capped current. Under a cap the connector check and `fuse_window_a`
  take `capped_a`, and a feed with no fuse is a `cap_without_fuse` violation; without one they take
  `current_a`. A feed's `connector_a` includes the PSU's output connector (`psu.connector`). Each
  output gives `fps`, the wire's rate at most the firmware's `min_frame_interval_s`. New warnings:
  `relies_on_cap_and_fuse` and `psu_full_white_overload`.
- **Session.** `Session.bind(mapping, grouping=..., catalog_digest=..., issues=..., limiter=...)`.
  Each frame passes the limiter before it is quantized. A frame that fails is dropped and the
  limiter stays bound. A session has no master dimmer, so the arrangement's `max_brightness`
  stays in the limiter, and `uncapped_watts` is the draw before both the brightness and the watt
  cap.

**Geometry (ws1b).** `build_glb(type_id: str, catalog: Catalog) -> bytes`. The output is
deterministic bytes. `assembly_digest(type_id, catalog) -> str` gives the URL key. In the GLB,
each part node carries `extras` `{"glow": "pixels"|"pixel_nearest"|"none", "gain": float}`, and
the root carries `extras.pixel_axis` `{"y0", "span", "count"}`. The same builder covers the
`attachment_type`s.

**Wiring and electrical (ws2).** `compile_rig` calls ws2's functions to produce `rig.slices` and
`rig.report`. The report includes `estimate_effect_power(frame_linear: np.ndarray) -> float` (W)
as a method or function that takes a linear-light float frame.

## HTTP (ws3 owns)

| Method and path | Response |
|---|---|
| `GET /health/live` | `200 {"ok": true}`, without touching the database |
| `GET /api/catalog` | the fixture types, attachment types, controllers, PSUs, cables and presets, each with display names, plus `digest` and `assembly_url` per fixture or attachment type |
| `POST /api/compile` (body: arrangement JSON) | `rig.to_json()`, plus `issues` and `report`; 422 with `issues` on errors |
| `GET /api/assembly/{digest}.glb` | the GLB, `Cache-Control: public, max-age=31536000, immutable` |
| `POST /api/arrangements` (body: arrangement) | `{"id": "<22-char base64url>"}`; the id is the first 128 bits of SHA-256 over the canonical JSON |
| `GET /api/arrangements/{id}` | the stored arrangement |
| `GET /api/looks` | `{name: look}`: the current look of each `examples/*.look.json`, by file name, in the looks file's form, ready to send as a `look` request (`PEWPEW_STUDIO_EXAMPLES` names another folder) |
| `GET /`, `GET /a/{id}`, `/assets/*` | the SPA from `studio-web/dist` when it exists |

## WebSocket `/ws/session` (ws3 owns)

Each session runs the aura that `python -m pewpew run` runs (ADR-025,
`pewpew.aura.pipeline.build_aura_pipeline`), with no looks file and no boards, taking whole
looks. It starts in `examples/tide.look.json`'s look on a 16 x 16 grid until the first bind.
Every message but `bind`, `pause` and `resume` is the preview's (`src/pewpew/sinks/preview.py`,
typed in `web/src/wire/protocol.ts`), with the same wire text: the session sends what
`pewpew.sinks.preview.StateTexts` and `answer_request` give.

- **Server to client, text:**
  - `{"type":"hello","n","fps","capabilities":["ack","look"]}`, sent on connect and after each
    successful bind. Every per-frame message below goes again after it;
  - the preview's per-frame messages, each sent with a frame when its text changes:
    `{"type":"status","error","source","path"}` (a render error, `"render"`, and the address of
    the part that raised it, or three nulls), `{"type":"declare","params":[spec]}` (every knob
    of the running look by address, such as `layers.base.waves.freq`),
    `{"type":"params","values":{address: value}}`, `{"type":"mod","values":{...}}` (the knobs a
    route drives, at most 10 times a second of engine time), `{"type":"aura",...}` (the aura
    state: the stack, the fade, the master) and `{"type":"catalog",...}` (the add-layer cards).
    There is no `health`;
  - `{"type":"ack","id","control"}`, to the client that asked, for an accepted request that
    carries an `id`;
  - `{"type":"refused","control","name","id","reason"}`, to the client that asked only.
    `control` is the request's `type` (null when it is not text), `bind` (with `issues` when
    the arrangement does not compile), `session` or `message`; `name` is the knob of a refused
    `set`. A request with no `id` that names no control is passed over. The reason never names a
    path;
  - `{"type":"bound","n","catalog_digest","issues"}`, always followed by a `hello`;
  - `{"type":"power","watts","uncapped_watts"}` at about 2 Hz: the effect power of the streamed
    frame under the arrangement's power cap, and of the same frame without it.
- **Server to client, binary:** a `<fI` header (engine `t` as float32, a uint32 sequence number,
  little-endian) followed by `n*3` uint8 display-ready RGB in rig pixel order. The frame is the
  capped one. The client drops
  any frame whose length is not `8 + 3n`.
- **Client to server, text:**
  - `{"type":"bind","arrangement":{...}}`, which compiles, rebinds the running look to the rig's
    mapping and fixture grouping, and keeps `t`. A look that cannot run on it (a strip for a
    look that folds a plane) is refused, and the old mapping stays;
  - any request of `pewpew.aura.control.REQUESTS`, as the preview takes it, with an optional
    `id` for its answer: `{"type":"set","name":<knob address>,"value"}` (the value in its kind's
    JSON form), `{"type":"look","look":{...},"fade"?}` (one look in the looks file's form, such
    as a `GET /api/looks` entry), `add_layer`, `remove_layer`, `move_layer`, `front`,
    `master`, `blackout`, `surprise`, `vary`, `arm` and `fire`. A request that needs a looks file
    (`recall`, `save`, `keep`, `delete`, `cycle`, `fade`), boards (`scan`, `rebind`) or a room
    (`blink`) is refused;
  - `{"type":"pause"}` and `{"type":"resume"}`, which the page sends when its tab is hidden or
    shown. A request that waits for the loop while it is paused is answered late.
- A session renders at 30 fps on its own thread. Frames cross to asyncio through
  `loop.call_soon_threadsafe` into a one-slot mailbox that keeps only the newest frame. A
  session pauses after 10 minutes with no inbound message.

## Run and package

- `python -m pewpew studio [--host 127.0.0.1] [--port 8000] [--db PATH]`. The store is
  `DATABASE_URL` when it is set (Neon Postgres, psycopg 3), and otherwise SQLite at `--db`
  (default: `PEWPEW_STUDIO_DB`, else `./studio.sqlite3`).
- `python -m pewpew run LOOKS --map <arrangement>.json` plays a looks file on a compiled
  arrangement. The arrangement's `power` block is the power limit, an
  `after` stage behind the master; `--max-watts W` and `--max-brightness B` replace its values.
  `--max-watts` needs an arrangement map, whose fixtures give the power model.
- The app factory is `pewpew.studio.app:create_app`, run with `uvicorn --factory`.
- `pewpew[studio]` = fastapi, uvicorn[standard], psycopg[binary], manifold3d. pydantic joins the
  core dependencies.
- `studio-web/` uses pnpm. `pnpm build` writes `studio-web/dist`. In development, Vite on 5173 proxies `/api`
  and `/ws` to 8000.
- The container listens on port 8000.

## Sources

- `src/pewpew/sinks/preview.py`, the module docstring and `message`
- `research/synthesis/decisions/ADR-025-one-effect-system.md`

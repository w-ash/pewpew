# Code review of the ws3 studio backend (high effort)

- **Reviewer:** an independent agent (Opus), not the author. It ran the `code-review` skill at
  high effort and read the author's report only after its own review.
- **Target:** `git diff studio...studio-ws3-server` at `d6c174e`, on 2026-10-22.
- **Status:** these are the findings as reported. The fix pass records what it did with each one
  in `ws3-fixes.md`.

## Findings, most severe first

**1. A paused session queues closures without bound.** CONFIRMED
- **Where:** `src/pewpew/studio/session.py:217`, `:254`, `src/pewpew/controls.py:37`.
- **Defect:** every `set`, `pattern` and `bind` appends a closure to `PacedLoop._calls`, an
  unbounded deque. While the session is paused nothing drains it.
- **Scenario:**
  - Sending `{"type":"pause"}` and then 40,000 `set`/`pattern` messages left 40,000 closures
    queued, with about 21 MB traced.
  - 500 `bind`s at n=12,800 raised peak RSS from 81 MB to 163 MB.
- **Fix:** coalesce instead of queueing. Keep one pending pattern slot, one pending bind slot and
  a name→value dict for sets, applied by a single closure per tick. Alternatively cap the queue
  and refuse when it is full.

**2. Paused sessions never time out, so their slots are held forever.** CONFIRMED (slots);
PLAUSIBLE (IPv6 bypass)
- **Where:** `src/pewpew/studio/app.py:275` (`timeout = None if session.paused`),
  `src/pewpew/studio/limits.py:57`.
- **Defect:** a session paused by the client (hidden tab) or by the idle timer keeps its
  admission slot as long as the socket lives. uvicorn's pings keep that socket alive.
- **Scenario:** with `max_sessions=2` and a 0.2 s idle timeout, both sessions were still
  registered after 2 s, and a third visitor got "the server is at its limit". With the defaults
  (20 sessions, 3 per address), 20 friends with background tabs lock everyone else out, or one
  actor with 7 addresses does.
- **IPv6:** admission keys on the full address, so a single host with an IPv6 /64 is not bounded
  by the 3-per-address cap. This part is reasoned, not run.
- **Fix:** close sessions that have been paused or idle past a second deadline. When at the cap,
  evict the session paused longest. Key IPv6 by /64.

**3. The 200-fixture cap misses preset groups, and there is no pixel cap.** CONFIRMED that the
pre-check passes; PLAUSIBLE impact.
- **Where:** `src/pewpew/studio/app.py:123-132`.
- **Defect:** the pre-check counts only the literal `fixtures` list. The post-check runs after
  `compile_fn` has already expanded everything.
- **Scenario:** `POST /api/arrangements {"groups":[{"preset":"ring","count":10000000}]}` passes
  the pre-check and reaches `compile_fn`.
- **Fix:** before compiling, count `fixtures` plus each group's `count` (or the product of
  `counts`). Also cap `rig.n`.

**4. The websocket size limit and the shutdown bound exist only in the CLI launcher.** CONFIRMED
- **Where:** `src/pewpew/__main__.py:336-337`, `src/pewpew/studio/app.py:290`.
- **Defect:** `ws_max_size=262144` and `timeout_graceful_shutdown=30` are set only in `_studio`.
  Under `uvicorn --factory pewpew.studio.app:create_app`, uvicorn's defaults apply: 16 MiB
  messages and no shutdown bound.
- **Scenario:** under bare `uvicorn --factory`, 1 MiB and 8 MiB text messages were fully
  accepted by the transport and only then refused by the app. The app's own check uses
  `len(text)`, which counts characters, so 262,144 four-byte characters (1 MiB) pass it.
- **Fix:** run `python -m pewpew studio` in production, and compare `len(text.encode())`.

**5. Compile has no rate or concurrency limit, and a bind serializes the rig on the event loop.**
PLAUSIBLE
- **Where:** `src/pewpew/studio/app.py:178-183` (`/api/compile`), `:324-331` (bind).
- **Defect:** `/api/compile` runs in the 40-thread pool with no per-address limit. A bind runs
  back-to-back per socket. `rig.to_json()` at `:331` runs on the asyncio thread, only to read
  `issues`.
- **Scenario:** a client looping compiles of 200-fixture arrangements takes threadpool and GIL
  time away from all 20 render threads. Each bind's `to_json` stalls every socket.
- **Fix:** add a per-address token bucket plus a global `BoundedSemaphore` around `compile_fn`.
  Take the issues from `rig.issues`, or run `to_json` inside the thread.

**6. An over-limit chunked body gets 400, not 413.** CONFIRMED
- **Where:** `src/pewpew/studio/limits.py:126-141`.
- **Defect:** FastAPI catches `_TooLarge` while parsing the body and re-raises it as an HTTP 400,
  so the middleware never sees it.
- **Scenario:** a 400 KiB chunked POST to `/api/arrangements` returns
  `400 {"detail":"There was an error parsing the body"}`. The body is still capped; only the
  status is wrong.
- **Fix:** when the limit is crossed, send the 413 from the middleware directly instead of
  raising.

**7. SaveLimiter's pruning scans every entry on each call once it holds more than 4096
addresses.** CONFIRMED
- **Where:** `src/pewpew/studio/limits.py:88-90`.
- **Defect:** the scan is O(n) per call, and it runs under the lock.
- **Scenario:** `allow()` took 0.11 ms at 4,296 addresses, 0.27 ms at 10,200 and 1.45 ms at
  20,200.
- **Fix:** use an `OrderedDict` and evict from the oldest end (O(1) amortized), with a hard size
  cap.

**8. The committed `openapi.json` is stale.** CONFIRMED
- **Where:** `openapi.json`, `src/pewpew/studio/app.py:153`.
- **Defect:** 5 of the 7 operationIds differ from what `create_app().openapi()` produces now.
- **Fix:** regenerate and commit it, and add a test that compares the committed file with
  `create_app().openapi()`.

**9. A stale frame after a `hello` resends the old pattern's `declare` and `params`.** CONFIRMED
(interleaving forced in the script)
- **Where:** `src/pewpew/studio/transport.py:95-108`.
- **Defect:** `pump` seeds `last_declare`/`last_params` from the new hello, then sends a frame
  payload that was queued before the swap.
- **Scenario:** a slow client got
  `hello:scale, frame:OLD, declare:speed, params:speed, frame:NEW, declare:scale`.
- **Fix:** in `_put_control`, when `declared` is set, clear `self._frame`, because any pending
  frame predates the hello.

**10. An admission slot leaks if `Session()` raises.** CONFIRMED (fault injected)
- **Where:** `src/pewpew/studio/app.py:241-243`.
- **Defect:** `Outbox`, `Session` and `registry.add` run after `admission.acquire` but outside the
  `try`/`finally` that releases it.
- **Fix:** move those three lines inside the `try`.

**11. Unexpected exceptions from input close the socket silently.** CONFIRMED
- **Where:** `src/pewpew/pattern.py:263`, `src/pewpew/studio/app.py:251`.
- **Defect:** `ParamSet.check` catches only `TypeError`/`ValueError`. `float()` of a 400-digit
  JSON integer raises `OverflowError`.
- **Scenario:** `{"type":"set","name":"speed","value":999…9}` (400 digits) closes the sender's
  socket instead of sending `refused`.
- **Fix:** catch `OverflowError` in `check`. In `_dispatch`, turn unexpected compile errors into
  `refused`, and log at WARNING.

**12. Contract fidelity gaps.** 422 shape CONFIRMED; the rest PLAUSIBLE
- A non-object body or invalid JSON returns FastAPI's `{"detail":[…]}` 422, not the contract's
  `{"issues"}` (`src/pewpew/studio/app.py:179,197`).
- `/api/catalog` calls `Catalog.to_json()` (`:167`), which contracts.md did not define. It is now
  pinned.
- Power is read only from `report.estimate_effect_power` (`:342`). It is now pinned as
  `CompiledRig.estimate_effect_power`.
- **Fix:** handle `RequestValidationError` and return `{"issues"}`, and follow the pinned
  contracts.

**13. Cheap requests trigger repeated work.** PLAUSIBLE, low
- `GET /api/assembly/<unknown>.glb` reruns `get_catalog()` on every miss, and `/api/catalog`
  recomputes digests on every request (`src/pewpew/studio/app.py:164-194`).
- `GET /api/arrangements/{id}` has no limit and opens a fresh Postgres/TLS connection per call
  (`src/pewpew/studio/store.py:85-108`).
- **Fix:** compute the digest map once per catalog, rate-limit GETs, and keep 404s away from the
  database where possible.

## Checked and sound

- **Renderer mutation:** `PacedLoop.call_soon` is the only path that changes a `Renderer`.
- **Thread lifecycle:** pause, resume and close race-free, and a socket dropped mid-bind cleans
  up.
- **SIGTERM** via `python -m pewpew studio`, with reading, stalled and dropped sockets: the
  server exited 0.21 s after the signal.
- **Hardening that holds:**
  - SQL is parameterized.
  - Only gallery patterns load.
  - Refusals carry no paths.
  - 500s are plain text.
  - SPA path traversal is blocked by `is_relative_to`.
- **Contract:** the routes, message types, the 8+3n frame, the content id, and the 600 s idle
  constant match contracts.md.
- **Determinism:** nothing in the session or transport render path reads a wall clock.
- **Fly-Client-IP:** Fly's page doesn't say whether a client-supplied value is overwritten
  (https://docs.fly.io/networking/request-headers).
- **Egress worst case** (inference): 20 sessions × 38 KB × 30 fps is about 83 GB/h, about
  $1.66/h at $0.02/GB.
- **Cleanup, not a bug:** `gallery_patterns` duplicates `pewpew.load._gallery`
  (`src/pewpew/load.py:230-241`).

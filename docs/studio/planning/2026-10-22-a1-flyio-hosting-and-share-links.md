# A1. Fly.io hosting and share links (Explore agent, default model, 2026-10-22)

Brief: current fly.io practice for a websocket app; storage for share-link JSON; websockets 17
behind a proxy and request bodies; hardening an unauthenticated app; Pyodide for comparison.

I confirmed most of your list. The main gaps: fly.io has no official doc on how an open websocket affects auto-stop, and I found no phone benchmarks for Pyodide. The docs.fly.io pages show no dates, so treat them as "current as fetched 2026-10-22". I've flagged sources older than about 12 months as **[OLD]**.

**1. fly.io for a websocket app**
- **Settings** ([docs.fly.io/reference/configuration](https://docs.fly.io/reference/configuration)):
  - `internal_port` defaults to 8080.
  - `auto_stop_machines` is `"off"`, `"stop"` or `"suspend"`, default `"off"`.
  - `auto_start_machines` defaults to `true`; `min_machines_running` defaults to `0`.
  - Concurrency `type` defaults to `"connections"`; the docs recommend `"requests"` for web services because the proxy can pool connections.
  - `soft_limit` defaults to 20 and decides "excess capacity". `hard_limit` has no default.
  - Health checks under `[[http_service.checks]]` take `grace_period`, `interval`, `timeout`, `method` (default get) and `path`. They need a 2xx and don't follow redirects.
- **Auto-stop:** a machine that is alone in its region is stopped only when it has "no traffic (a load of 0)". The check runs "every few minutes" ([fly-proxy-autostop-autostart](https://docs.fly.io/reference/fly-proxy-autostop-autostart)).
  - *Inference:* with `type="connections"`, an open websocket counts as load, so one forgotten tab keeps the machine billing. Add a server-side idle-session timeout.
  - Since 2026-04-09 the proxy sends a WebSocket close frame before it stops or suspends a machine ([community post 27544](https://community.fly.io/t/fly-proxy-now-gracefully-terminates-websocket-connections-before-stopping-suspending-a-machine/27544)).
- **Suspend:** needs 2 GB RAM or less and no swap. Resume takes "a few hundred ms", against about 2+ s for a cold start. TCP connections may be dead after resume ([suspend-resume](https://docs.fly.io/reference/suspend-resume)).
- **Idle timeouts:**
  - The config has `http_options.idle_timeout`, but no default or maximum is documented.
  - The often-quoted 60 s figure comes only from **[OLD]** forum posts ([thread 3007](https://community.fly.io/t/is-it-possible-to-increase-the-timeout-to-120-sec/3007)).
  - A 2026-10-08 staff reply says a fixed 30 s `TCP_USER_TIMEOUT` resets connections whose receive window stays at zero, and it can't be changed ([thread 28755](https://community.fly.io/t/fly-proxy-resets-a-stalled-http-stream-after-30s-on-edge-and-flycast-hops-http-options-idle-timeout-has-no-effect/28755)).
  - *Inference:* a slow client that can't keep up with the frames gets cut off, so drop frames rather than queue them.
- **TLS:** the `tls` handler terminates TLS with Fly-managed certificates and forwards plain traffic to the app ([networking/services](https://docs.fly.io/networking/services)). So the page uses wss:// while the app speaks plain ws.
- **Client IP:** use the `Fly-Client-IP` header ([request-headers](https://docs.fly.io/networking/request-headers)).
- **Cost** ([about/pricing](https://docs.fly.io/about/pricing)):
  - shared-cpu-1x 256 MB is $2.19/mo if running all month; 512 MB is $3.69/mo.
  - A stopped machine costs $0.15/GB/mo of root filesystem.
  - There is no free tier for new organisations, only a trial. A small-invoice waiver: not found.
  - Outbound bandwidth is $0.02/GB in North America and Europe.
  - *Inference:* 90 KB × 30 fps ≈ 9.7 GB per viewer-hour, about $0.19/hour. That is likely your biggest cost, so cap frame size and session length.
  - *Inference:* 512 MB is the sensible minimum with numpy loaded.
- **Dockerfile for uv** ([uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/), dated 2026-10-21, uv 0.13.5):
  - Start from a slim Python image and copy uv in with `COPY --from=ghcr.io/astral-sh/uv:<pinned>`.
  - Set `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy` and `UV_NO_DEV=1`.
  - Run `uv sync --frozen --no-install-project` with a cache mount, then `COPY .` and `uv sync --locked`.
  - Optionally use multi-stage with `--no-editable` and copy only `.venv`, then start with `CMD ["/app/.venv/bin/..."]`.

**2. Storing share-link JSON**
- **Volumes:** a volume attaches to only one machine and isn't replicated. Snapshots are daily, kept 5 days by default (1–60 configurable). The docs say "Always provision at least two volumes" ([volumes/overview](https://docs.fly.io/volumes/overview)). A volume costs $0.15/GB/mo; snapshots are $0.08/GB/mo with the first 10 GB free.
- **Tigris:** `fly storage create` sets `BUCKET_NAME`, `AWS_ENDPOINT_URL_S3` and the access keys, and usage appears on the Fly bill ([docs.fly.io/tigris](https://docs.fly.io/tigris)). The free tier is 5 GB, 10k writes and 100k reads per month, then $0.02/GB, with no egress fees ([tigrisdata.com/pricing.md](https://www.tigrisdata.com/pricing.md), undated).
- **LiteFS:** its docs say Fly can't provide support, it is pre-1.0, and it must not be combined with autostop ([fly.io/docs/litefs](https://fly.io/docs/litefs/)). LiteFS Cloud was shut down **[OLD]** ([thread 20829](https://community.fly.io/t/sunsetting-litefs-cloud/20829)).
- *Inference:* Tigris is the simplest durable choice. It costs nothing at this scale, survives losing the machine, and suits write-once blobs.

**3. websockets 17.x**
- Your notes are confirmed. In 17.0.1's `http11.py`, line 183 raises `NotImplementedError` on any `Transfer-Encoding` header. Lines 186–190 raise `ValueError("unsupported request body")` when `Content-Length` isn't 0 (checked via curl of the 17.0.1 tag: [line 183](https://github.com/python-websockets/websockets/blob/17.0.1/src/websockets/http11.py#L183), [lines 186–190](https://github.com/python-websockets/websockets/blob/17.0.1/src/websockets/http11.py#L186-L190)).
- 17.3, released 2026-10-19 per [PyPI](https://pypi.org/project/websockets/), still refuses bodies at [lines 202–203](https://github.com/python-websockets/websockets/blob/17.3/src/websockets/http11.py#L202-L203). So `process_request` can't take a POST. *Inference:* send saves as websocket messages instead.
- The FAQ says serving HTTP is "out of scope" for websockets, with "limited support" via `process_request` ([faq/server](https://websockets.readthedocs.io/en/stable/faq/server.html)).
- **Sync vs asyncio:**
  - asyncio is "ideal for servers that handle many clients concurrently"; threading "can be a good choice for clients" ([reference index](https://websockets.readthedocs.io/en/stable/reference/index.html)).
  - The deploy page says "Don't scale with threads. Scale only with processes." ([deploy](https://websockets.readthedocs.io/en/stable/deploy/index.html)).
  - *Inference:* the sync server works for tens of connections, but asyncio is the documented choice for public servers.
- **Keepalive and limits:** pings every 20 s with a 20 s timeout; `max_size` is 1 MiB and `max_queue` is 16 ([sync server reference](https://websockets.readthedocs.io/en/stable/reference/sync/server.html), 17.2; [keepalive](https://websockets.readthedocs.io/en/stable/topics/keepalive.html)).

**4. Hardening and share links**
- **ID length:** OWASP requires at least 64 bits of entropy from a cryptographic random generator ([OWASP Session Management cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)). `secrets.token_urlsafe` gives about 1.3 characters per byte; its "32 bytes" advice dates from 2015 **[OLD]** ([Python 3.15.1 docs](https://docs.python.org/3/library/secrets.html)).
- **Excalidraw:** uploads an encrypted blob and puts the 128-bit key (22 characters) in the `#fragment`, which never reaches the server **[OLD, 2020]** ([blog](https://plus.excalidraw.com/blog/end-to-end-encryption)).
- **tldraw:** has editable links plus read-only links, and frozen snapshot links **[OLD, 2023]** ([release notes](https://tldraw.dev/blog/release-notes-20230223)). In 2025, snapshots became republishable **[OLD]** ([whats-new-2025](https://tldraw.dev/blog/whats-new-2025)).
- **three.js editor:** "Publish" zips the project on the client and has no hosted link ([`editor/js/Sidebar.Project.App.js`](https://github.com/mrdoob/three.js/blob/r186/editor/js/Sidebar.Project.App.js) [line 3](https://github.com/mrdoob/three.js/blob/r186/editor/js/Sidebar.Project.App.js#L3) and [lines 80–84](https://github.com/mrdoob/three.js/blob/r186/editor/js/Sidebar.Project.App.js#L80-L84), r186).
- **p5.js:** has share and embed links; whether it needs an account is unclear **[OLD]** ([forum](https://discourse.processing.org/t/embedding-p5-js-web-editor-in-external-site/18400)). **Shadertoy:** not found.
- **Inference (no source found for standard numbers):**
  - Use immutable snapshot links with an ID from `token_urlsafe(16)`, which is 128 bits. "Edit" makes a fork with a new ID. That's the simplest and safest model without accounts.
  - Per-IP limits: about 2–3 websockets per `Fly-Client-IP`, set inbound `max_size` to about 64 KiB, about 10 saves per minute per IP, and a total storage cap.

**5. Pyodide (for the rejected-alternatives comparison)**
- The latest stable is 314.0.7, released 2026-09-14 per [npm](https://registry.npmjs.org/pyodide/latest); 315.0.0-alpha.2 is the next tag. 314.0 came out 2026-06-09 on Python 3.14.2 ([release post](https://blog.pyodide.org/posts/314-release)).
- **Download size, measured by HEAD requests to [jsDelivr](https://cdn.jsdelivr.net/npm/pyodide@314.0.7/) for 314.0.7:**

| File | Raw | Brotli |
|---|---|---|
| `pyodide.asm.wasm` | 9.6 MB | 3.44 MB |
| `python_stdlib.zip` | 2.55 MB | 2.51 MB |
| numpy 2.4.6 wheel | 2.96 MB | 2.93 MB |

  That totals about **8.9 MB over the wire** (about 15 MB raw).
- **Startup and speed:** the roadmap page still states 6.4 MB, 4–5 s to initialise, and "3x to 5x slower than native Python". That text dates from old releases, so treat it as stale ([roadmap](https://pyodide.org/en/stable/project/roadmap.html)).
- **numpy vs native:** one 2023 benchmark measured about 3.8× slower **[OLD]**, hardware unknown ([Measurements.md](https://git.sciprog.center/teldufalsari/advanced-python-homework/src/branch/main/benchmark/Measurements.md)).
- **Phone startup time:** not found.

## Sources

- https://docs.fly.io/reference/configuration
- https://docs.fly.io/reference/fly-proxy-autostop-autostart
- https://community.fly.io/t/fly-proxy-now-gracefully-terminates-websocket-connections-before-stopping-suspending-a-machine/27544
- https://docs.fly.io/reference/suspend-resume
- https://community.fly.io/t/is-it-possible-to-increase-the-timeout-to-120-sec/3007
- https://community.fly.io/t/fly-proxy-resets-a-stalled-http-stream-after-30s-on-edge-and-flycast-hops-http-options-idle-timeout-has-no-effect/28755
- https://docs.fly.io/networking/services
- https://docs.fly.io/networking/request-headers
- https://docs.fly.io/about/pricing
- https://docs.astral.sh/uv/guides/integration/docker/
- https://docs.fly.io/volumes/overview
- https://docs.fly.io/tigris
- https://www.tigrisdata.com/pricing.md
- https://fly.io/docs/litefs/
- https://community.fly.io/t/sunsetting-litefs-cloud/20829
- https://github.com/python-websockets/websockets/blob/17.0.1/src/websockets/http11.py#L183
- https://github.com/python-websockets/websockets/blob/17.0.1/src/websockets/http11.py#L186-L190
- https://pypi.org/project/websockets/
- https://github.com/python-websockets/websockets/blob/17.3/src/websockets/http11.py#L202-L203
- https://websockets.readthedocs.io/en/stable/faq/server.html
- https://websockets.readthedocs.io/en/stable/reference/index.html
- https://websockets.readthedocs.io/en/stable/deploy/index.html
- https://websockets.readthedocs.io/en/stable/reference/sync/server.html
- https://websockets.readthedocs.io/en/stable/topics/keepalive.html
- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- https://docs.python.org/3/library/secrets.html
- https://plus.excalidraw.com/blog/end-to-end-encryption
- https://tldraw.dev/blog/release-notes-20230223
- https://tldraw.dev/blog/whats-new-2025
- https://github.com/mrdoob/three.js/blob/r186/editor/js/Sidebar.Project.App.js
- https://github.com/mrdoob/three.js/blob/r186/editor/js/Sidebar.Project.App.js#L3
- https://github.com/mrdoob/three.js/blob/r186/editor/js/Sidebar.Project.App.js#L80-L84
- https://discourse.processing.org/t/embedding-p5-js-web-editor-in-external-site/18400
- https://registry.npmjs.org/pyodide/latest
- https://blog.pyodide.org/posts/314-release
- https://cdn.jsdelivr.net/npm/pyodide@314.0.7/
- https://pyodide.org/en/stable/project/roadmap.html
- https://git.sciprog.center/teldufalsari/advanced-python-homework/src/branch/main/benchmark/Measurements.md

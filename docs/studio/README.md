# pewpew Gallery

The Gallery is the hosted app (code name `studio`, on fly.io). It serves the Console's own page
and shows a layout someone shared, read-only, in 3D. A visitor plays with looks on that layout,
keeps them for the visit, and exports them. The Console is the engine's page; it publishes a
layout and its looks to the Gallery (ADR-024, 2026-11-08 amendment).

## Run it locally

```
uv sync --extra studio
uv run python -m pewpew studio          # http://127.0.0.1:8000, SQLite at ./studio.sqlite3
```

`/` runs the example arrangement `golden-rings.json` with the example looks. `/a/{id}` runs a
share. No Node is needed: the Gallery serves the committed Console build. To publish from a local
Console to a local Gallery, start the Console on an arrangement with
`python -m pewpew run LOOKS --map RIG.arrangement.json --preview --gallery http://127.0.0.1:8000`.

## Routes

| Route | Answer |
|---|---|
| `GET /`, `GET /a/{id}` | the Console page, titled `pewpew Gallery`, never cached; `/a/{id}` is 404 for an unknown id |
| `GET /assets/...` | the build's hashed files, immutable, gzipped when accepted |
| `GET /parts.json`, `GET /assembly/{digest}.glb` | the 3D view's parts and models, as the engine serves them |
| `POST /api/shares` | publish a share (below) |
| `GET /health/live` | liveness; does not touch the database |
| WebSocket `/ws?a=<id>` | one session on that share; no `a` means the default share |

No route sends CORS headers.

## What a visitor can do

The hello's `capabilities` are `ack`, `look`, `export`, `pause` and `gallery`. The layout is
read-only. The visitor's looks are an in-memory book for the visit: save, rename, favorite, and
`export` them as a looks file. Nothing is stored on the server, and the Gallery never sends
`health`, `arrangement` or `report`. The idle cycle is off: a session plays what the visitor
picks. A session pauses after 10 minutes without a message (`pause` and `resume`).

A session holds bounded memory, since the Gallery is public:

- Its book grows to the size of a share at most (256 KiB of compact JSON, 64 looks); a save or a
  rename that grows it past that is refused.
- One `export` at a time is on its way (from the request until its `exported` is sent), and at
  most 10 a minute, 3 at once; another is refused.
- Its queue of discrete messages holds at most 256 messages and 1 MiB of text (a larger hello goes
  alone); past either, the socket closes, even mid-send to a client that does not read.

A page whose connection is refused or closed before a hello (a full Gallery, an unknown share)
reconnects after twice its last wait, to 10 s, less up to half at random, and shows the
refusal's reason in place of the wait. A stored share that cannot be read is refused with "this
share can't be opened" and the socket closes normally.

## The share envelope

```json
{"format": "pewpew.share", "version": 1, "arrangement": {...}, "looks": {...looks file v4...}}
```

- `arrangement`: every `controllers[].host` removed, no `plan` (no floor plan in v1), and no
  `notes`. The arrangement's `notes` are internal and never leave the machine; its `name` and
  `public_notes` travel with the share.
- `looks`: only the chosen looks, each checked with `pewpew.lab.check.ready`; no `triggers`, no
  `notes`.
- The id is the first 128 bits of SHA-256 over the canonical JSON (sorted keys, compact),
  base64url, 22 characters (`src/pewpew/share.py`).
- An older stored link is a bare arrangement; it opens with the example looks.
- Limits: the canonical envelope at most 256 KiB; at most 200 fixtures and no list in the
  arrangement longer than 200; the looks file's own limits (64 looks).

## Publish from the Console

On an attended arrangement run the Console offers Publish (the hello has `publish`). Pick looks
(default: the current look and the favorites) and press Next. The page then shows, as plain
text, everything the share makes public: the arrangement's name, its public notes (with a switch
to leave them out of this share) and the looks' names, then "This is public: anyone with the link
sees this layout and these looks. Board addresses are removed." What is right to make public is
the author's call, share by share. Press Publish. The
page submits a top-level form POST to `{gallery}/api/shares` in a new tab, with `rel="noreferrer"`
so the Console's LAN address is not sent. The gallery is `--gallery URL`, default
`https://pewpew.fly.dev`. The Gallery answers `303` to `/a/{id}`, or with a plain-text error:
413 too large, 415 wrong content type, 422 not a share, does not check or does not compile,
429 more than 10 shares a minute from one address, 503 busy compiling or the store cannot
write ("the Gallery can't store shares right now"). A share is cached only once it is stored.

The Console's "export looks" saves the same looks as a looks file (`export` with `share: false`).

## Removed

The studio's own page and editor, its mock mode, the generated API client (orval, msw, TanStack
Query), `scripts/export_openapi.py`, the Dockerfile's Node stage, `/api/compile`, `/api/catalog`,
`/api/looks`, `/api/assembly/*`, `/api/arrangements*`, `/ws/session`, `/api/docs` and
`/api/openapi.json`. The files below are the record of how it was built, written before this
change; where they name those routes or the studio page, they are history.

## Records

- [`plan.md`](plan.md): the plan the maintainer approved on 2026-10-22. It covers the decisions,
  the workstreams and the verification.
- [`domain-model.md`](domain-model.md): the rig domain model. It has three parts: the catalog,
  the arrangement, and the wiring and power. This is the design every workstream builds to.
- [`planning/`](planning/): the planning reports, verbatim, from 2026-10-22 (the A0 handoff
  that started the work is in the project's notes, not in this repo):
  - [A1](planning/2026-10-22-a1-flyio-hosting-and-share-links.md): fly.io hosting and share
    links;
  - [A2](planning/2026-10-22-a2-threejs-viewer-and-editor.md): the three.js viewer and editor;
  - [A3](planning/2026-10-22-a3-power-wiring-controllers.md): power, wiring and controller
    modeling;
  - [A4](planning/2026-10-22-a4-fixture-model-prior-art.md): prior art for fixture, placement
    and power models;
  - [A5](planning/2026-10-22-a5-stack-and-libraries.md): the stack and libraries as of October
    2026.

The fixture record for the 1M LED Pixel Bar (INV-001) and the 1.5M 360 LED Tube (INV-002) is
the maintainer's fixture notes, which are not public. The record IDs these docs cite (INV-, PRT-,
RES-, Q-) are from those notes.

[`prototype/`](prototype/) holds a copy of the three.js prototype the studio grew from, made
2026-10-22: the viewer `golden-tubes-3d.html` (an artifact body with no html/head/body wrapper),
its renders `overview.png`, `point.png` and `eye.png`, and the 2D generators `rings.py` and
`tubes.py` with their SVGs. The visual check compares against `prototype/overview.png`.

## Sources

- The maintainer's fixture notes (fixture record, not public)
- `docs/studio/prototype/golden-tubes-3d.html`, `overview.png`, `point.png`, `eye.png`, `rings.py`, `tubes.py`

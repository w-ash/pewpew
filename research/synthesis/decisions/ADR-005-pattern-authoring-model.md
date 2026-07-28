# ADR-005: Pattern authoring model — Pixelblaze-shaped, Python-real, NumPy-executed

Status: Accepted (2026-07-26); amended 2026-07-27 (private per-pixel
state buffers — see Amendment below)

## Context

The authoring surface is pewpew's core product decision. Pixelblaze's
per-pixel-pure-function model (normalized world coords, 0–1 phase idioms,
before/render split) is the acknowledged best-in-class UX but runs on a
closed VM; led-control translated it to Python but pays per-pixel CPython
dispatch (~22.5k px/s ceiling); LedFx exposes raw array semantics that only
contributors author against. No system combines the friendly surface with
vectorized execution (comparison-matrix gap #4).

## Decision

- Patterns are classes with **`before_render(dt, features)`** (per-frame
  state advance) and **`render(x, y, z, index)`** — a pure function over
  **coordinate arrays** in normalized 0–1 world units, returning float32
  linear RGB (ADR-001). Scalar-looking NumPy-compatible expressions
  broadcast; the author never writes a pixel loop.
- 0–1 phase/time built-ins (`time()`, `wave()`, `triangle()`, `square()`)
  ship as the standard idiom kit.
- **Frame buffer persists** across frames (`self.pixels`) for trails/decay.
  (amended 2026-07-27, private per-pixel state buffers: `self.pixels` is no
  longer the *only* persistent per-pixel state — it becomes the engine's own
  entry in a registry of buffers declared via `self.buffer(...)` in `setup`.)
- **Motion is time-parameterized** (`t`/`dt`), never frame-counted (Q-5).
- **Errors never stop the show**: per-frame exception containment, visible
  error state, last-good pattern keeps running.
- **No sandboxing** for the trusted local case; patterns are plain Python
  modules (a shared-gallery mode may revisit).
- Typed parameters per ADR-006; live reload semantics per architecture §8.

## Consequences

- One authoring contract spans host (NumPy) and wearable (ulab) tiers
  (ADR-008).
- The bet: authors accept array semantics behind a scalar-looking surface —
  branching (`if` vs `np.where`) is the known friction; Phase-0 prototype
  item #2 gates this before the API freezes.
- Golden-frame testing becomes possible because render is pure
  (architecture §8).

## Verification (Phase-0 item 2, 2026-07-16)

Prototyped the contract (`bench/authoring/`) and authored the five
canonical patterns against it: zero blockers, 17 recorded stumbles (4 hit
/ 13 expertise-shielded), all patterns ≤33 author-facing lines,
deterministic. `np.where` translation proved mechanical; real friction
is threshold/dtype edges, per-pixel state beyond the output buffer, and
time/RNG discipline — all mitigable in the idiom kit. Full inventory:
`bench/results/authoring-2026-07-16.md`. **Status: bet confirmed —
Accepted**, with the kit additions listed there scheduled before Phase 1
pattern authoring opens.

## Evidence

- [S680:README.expressions.md#L19-L70] Pixelblaze's beforeRender/render
  split, 0–1 idioms, and live-compile UX — the model to match.
- [S660:ledcontrol/animationfunctions.py#L10-L26][S660:README.md#L17-L24]
  led-control proves the surface in Python and documents the per-pixel
  ceiling (~150 fps × 150 px on Pi Zero).
- [S207] ARTI-FX: WLED's own community reimplemented the Pixelblaze model
  to escape compiled-in effects — second independent reimplementation.
- [S400][S211] Vectorization buys ~10× even on an RP2040 (40 ms → 4 ms per
  256-px frame) — the execution-side justification. Caveat: both IDs are
  the same todbot article — one author, one measurement, not two sources.
- [S630:ledfx/effects/__init__.py#L479-L547] LedFx's persistent
  `self.pixels` convention; [S715:docs/history/decisions.md#L540-L549]
  projectMM learned auto-clearing breaks every trail effect.
- [S660:ledcontrol/animationcontroller.py#L418-L434][S504] led-control's
  pulsing-red error frame and Pixelblaze's crash-proof editor — the error
  containment precedents.
- [S304][S680:README.mapper.md#L12-L36] Normalized world units with
  Fill/Contain policy — the portability mechanism. (Both IDs resolve to
  the same Pixelblaze mapper document — seed URL vs pinned repo copy.)

## Rejected alternatives

- **Per-pixel interpreted dispatch** (led-control) — 22.5k px/s ceiling
  even with C helpers [S660:README.md#L17-L24][S210].
- **Raw array semantics as the authoring surface** (LedFx) — contributor-
  oriented; registry classes + schema boilerplate + restart per edit
  [S630:ledfx/effects/__init__.py#L273-L340][S208].
- **Custom expression language + VM** (Pixelblaze [S681], ARTI-FX [S207])
  — compiler+VM maintenance burden; deferred, not adopted (revisited for
  the wearable in ADR-008).
- **GPU/shader-first authoring** — context fragility headless, image-space
  thinking; steal ISF manifests and field-sampling instead [S213][S214].
- **RestrictedPython sandboxing** (led-control) — taxes the hot loop and
  still can't stop unbounded loops
  [S660:ledcontrol/animationcontroller.py#L228-L282].
- **Compiled-in effect catalog** (WLED) — the authoring bottleneck its own
  power users routed around [S205][S207].

## Amendment (2026-07-27) — private per-pixel state buffers

Resolves the open question left by stumble #17 of
`bench/results/authoring-2026-07-16.md` ("decide in Phase 1: sanctioned
private per-pixel state buffers alongside `self.pixels`"). Answer: **yes,
sanctioned and engine-managed.**

### Decision

- A new **`setup(self, n, x, y, z, index)`** lifecycle hook is called once
  per (pattern, mapping) binding and hands the pattern its coordinate
  arrays.
- Inside `setup` **only**, a pattern declares persistent state with
  **`self.buffer(name, shape, dtype=float32, fill=0.0)`**, which allocates
  the array, sets it as `self.<name>`, and returns it. The engine registers
  each buffer and owns its lifecycle: zero on rebind, reallocate on mapping
  change (resize re-zeros — no resampling semantics are invented), and
  carry across hot reload by name+shape. `self.pixels` becomes simply the
  engine's own entry in that registry.
- The registry maps name → **spec**, never name → array identity. Authors
  legitimately rebind (`self.heat = np.maximum(self.heat - cool, 0.0)` is
  the study's own fire spelling), so the engine re-reads `getattr` fresh;
  identity tracking would silently stop tracking at the first rebind.
- **Shape is free-form**, so an internal field at its own resolution
  (fire's 16×32 heat grid, stumble #12) gets the same sanctioned home as an
  `(N,)`-shaped per-pixel array.
- **`render` stays pure**: it receives read-only views
  (`setflags(write=False)`) of `self.pixels` and of every declared buffer.
  Only `setup` and `before_render` may write. RNG draws remain confined to
  `setup`/`before_render`.

Coords-at-setup is the actual unlock. #17's bind was that `before_render`
never sees coordinates, so per-pixel state had to be laundered through the
output buffer — which is what ratcheted the sparkle overlay to permanent
white. Giving `setup` the coords lets per-pixel state be advanced in
`before_render` with full coordinate knowledge while `render` stays pure.

### Consequences

- Both undocumented idioms the study surfaced get a first-class home: the
  internal-field idiom (#12) and additive per-pixel overlays (#17) stop
  being workarounds over `self.pixels`.
- Render purity — the property golden-frame testing and determinism rest on
  (architecture §8) — is preserved rather than traded away.
- The engine gains buffer-lifecycle responsibility it did not have: a
  registry, rebind zeroing, and reallocation on mapping change.
- The hot-reload story in `docs/backlog/v0.2.x.md` now depends on this —
  buffers must carry across reload too, not just params.
- Unblocks "Port the upgraded fire to Python" in
  `docs/backlog/unscheduled.md`.
- `setup` adds a third lifecycle method to the contract authors must learn;
  the surface is no longer just `before_render`/`render`.

### Evidence

- [S680:README.expressions.md#L86,L93] Pixelblaze arrays are first-class
  persistent globals (`array(size)`, "passed around just like any other
  type", never freed) — the model ADR-005 copies already sanctions
  per-pixel state beyond the output buffer. Load-bearing caveat: it buys
  that with an **impure render** — `beforeRender(delta)` receives only
  elapsed milliseconds, no coordinates
  [S680:README.expressions.md#L23], and the docs assume globals may be
  written inside `render()` [S680:README.expressions.md#L35]. That is
  stumble #17's exact bind in the incumbent, and its resolution is the
  trade we decline: we take the sanction, not the mechanism.
- [S218] ISF: `PERSISTENT: true` per `PASSES` entry, "the ISF host will
  automatically create buffers to render into", and those buffers "stay
  with the ISF file for as long as it exists"; optional `FLOAT` and
  per-buffer `WIDTH`/`HEIGHT` let a buffer live at its own resolution —
  precedent for engine-managed buffers declared up front at an
  author-chosen shape. (Same project as [S214], cited in ADR-006 for the
  typed-param manifest — one lineage, not two sources.)
- [S219] Shadertoy is the independent third lineage: Buffers A–D persist as
  32-bit float render targets "initialized to 0", and the canonical idiom
  is to "make your buffer read the same texture it produces (i.e. previous
  state vs next state)". It also independently motivates re-zeroing on
  geometry change — persistent buffers "won't keep valid if resolution
  changes while running: consider testing change, or a magic key to
  reinitialize."
- [S630:ledfx/effects/__init__.py#L479-L547] and
  [S715:docs/history/decisions.md#L540-L549] (already cited above) — the
  persistent-buffer convention this generalizes, and the auto-clear lesson
  that the registry's zero-*on-rebind*-only rule respects.
- In-repo study evidence (not an S-ID): stumbles #12 and #17 of
  `bench/results/authoring-2026-07-16.md`, both `hit`, are what forced the
  question.

### Rejected alternatives

- **An ISF-style second per-pixel *pass*** — e.g. `update(x, y, z, index,
  dt)`, permitted to write buffers. More faithful to multipass shaders
  [S218][S219], but it doubles the array-shaped contract surface (two
  per-pixel entry points to teach, test and freeze) to cover a need that
  coords-at-setup already covers.
- **Pixelblaze's own answer — let `render` write globals**
  [S680:README.expressions.md#L35]. The smallest change and the
  incumbent's choice, but it forfeits render purity, and an impure render
  over the output buffer is precisely the feedback path that produced
  #17's ratchet to white.
- **Leave `self.pixels` as the only per-pixel state** — the status quo the
  study falsified: #12's neighbor stencil is inexpressible over it and
  #17's additive overlay ratchets through it.
- **Author-managed buffers** (plain `self.foo = np.zeros(...)` in
  `__init__`) — costs no engine machinery, but nothing then zeroes on
  rebind, resizes on mapping change, or carries across hot reload, and the
  engine cannot hand `render` a read-only view of state it does not know
  about.

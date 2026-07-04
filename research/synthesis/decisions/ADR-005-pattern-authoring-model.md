# ADR-005: Pattern authoring model — Pixelblaze-shaped, Python-real, NumPy-executed

Status: Proposed (2026-07-03)

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

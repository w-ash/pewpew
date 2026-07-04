# ADR-011: Language & performance strategy — Python + NumPy core, compiled tier optional

Status: Proposed (2026-07-03)

## Context

pewpew's differentiators (live Python authoring, pip-installable
engine-as-library, one contract across host and ulab tiers) require Python
at the surface. The question is whether Python can also be the execution
substrate at room scale (R-9: ≥20k px × 60 fps ≈ 1.2 M px·frames/s on a
Pi 5-class host), or whether a compiled core is needed under it. The
evidence base is honest but incomplete: vectorization's ~10–100× gain over
per-pixel Python is well-attested, but **no published NumPy benchmark
exists at 5k–50k pixels**.

## Decision

- **Python end-to-end, NumPy-vectorized hot paths.** Patterns, pipeline
  stages (ADR-001), map gathers (ADR-007), and DSP (ADR-009) are all
  whole-array float32 operations; per-pixel Python never appears on the
  frame path.
- Author-facing code stays scalar-looking (ADR-005); the engine evaluates
  it over coordinate arrays.
- **An optional Numba/compiled tier is planned for, not adopted**: the
  architecture keeps pattern evaluation pure and array-in/array-out so a
  `@njit` or compiled-kernel escape hatch can slot under specific patterns
  without API change.
- **R-9 feasibility is explicitly deferred pending benchmark** —
  prototype item #1 (per-pixel vs NumPy vs Numba at N ∈ {300, 3k, 30k} on
  desktop and Pi 5) runs in Phase 0, before the engine core hardens. If
  NumPy alone misses R-9 on a Pi 5, the compiled tier is promoted from
  optional to required for the room tier; the product shape is unchanged.

## Consequences

- The engine ships as a normal pip package; contributors write Python only.
- Everything on the frame path must be expressible as array ops — a real
  design constraint (e.g. no data-dependent per-pixel recursion).
- Wearable-tier parity falls out for free: ulab mirrors the same array
  semantics (ADR-008).

## Evidence

- [S660:README.md#L17-L24][S210] Per-pixel interpreted Python caps at
  ~22.5k px/s even with C helpers (led-control) — the ceiling that rules
  out the naive approach.
- [S400][S211] Vectorization measured at ~10× even on an RP2040
  (40 ms → 4 ms per 256-px frame). Caveat: both IDs are the same todbot
  article — one author, one measurement, not two sources. The "host CPUs
  gain 1–2 orders of magnitude" extrapolation is NOT measured by that
  source; it is RA-05's inference, tagged [NEEDS-VERIFICATION] there, and
  gates on the same Phase-0 benchmark as R-9.
- [S630][S011] LedFx drives many devices at a 60 fps tick from a desktop
  with vectorized effects — production proof at moderate scale, though no
  published px/s ceiling exists.
- [RA-05 open questions] The 5k–50k px NumPy measurement gap is documented
  — the single-source-style caveat this ADR carries: **the room-scale
  throughput claim (R-9) is unverified and gates on prototype item #1.**

## Rejected alternatives

- **C++/Rust engine core with Python bindings** — rejected for
  build/maintenance burden and contributor accessibility (a two-language
  codebase; "contributors write Python only" no longer holds), not for
  installability or authoring: compiled cores ship as pip wheels routinely
  (NumPy, the adopted substrate, is itself one) and live Python pattern
  authoring is unaffected by the core's language. The engine-as-library
  gap pewpew targets (comparison-matrix §"what no single system has"
  [S011][S017][S030]) is served either way; reconsidered only if the
  Phase-0 benchmark fails even with Numba.
- **Per-pixel Python with C helpers** (led-control) — measured ceiling
  [S660:README.md#L17-L24].
- **Custom bytecode VM** (Pixelblaze) — compiler+VM maintenance for
  performance NumPy already reaches on hosts
  [S681:pixelblaze/pixelblaze.py#L1490-L1512][S405].
- **GPU/shader execution core** — headless-context fragility and
  image-space authoring; field-sampling stays an optional content source
  only [S213][S214].
- **Adopting Numba as a hard dependency now** — compilation latency and
  install weight against unproven need; kept as the planned escape hatch
  pending the benchmark [RA-05 open questions][S211].

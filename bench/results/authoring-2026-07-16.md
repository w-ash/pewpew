# Authoring-surface prototype — stumble inventory (§12 item 2)

**Date:** 2026-07-16 · **Gates:** ADR-005 (pattern authoring model)
**Machine artifact:** [`authoring-2026-07-16.json`](authoring-2026-07-16.json)
**Code under study:** `bench/authoring/` (surface prototype + 5 patterns)

## Question

Do authors tolerate the vectorized surface — scalar-looking code over
coordinate arrays (`before_render(dt, features)` + `render(x, y, z, index)` +
persistent `self.pixels`)? §12 item 2's metric: write fire, comet, plasma,
GEQ, and a 3D SDF; count the `if` → `np.where` stumbles. No prior art in the
LED space [RA-05].

## Bias disclosure (read first)

These patterns were written by an author who already knows NumPy. Raw counts
therefore **undercount novice friction**: most entries below are flagged
`shielded` — the broken scalar spelling was avoided only because the author
knew the array idiom in advance. A scalar-thinking author would have *hit*
each shielded entry. Entries flagged `hit` genuinely tripped even the
NumPy-fluent author (empirically demonstrated in each case). Treat `hit` as
a floor and `hit + shielded` as the realistic novice-facing count.

## Results at a glance

| Pattern | Fixture | Author-facing LOC | np.where | Stumbles | Character |
|---|---|---|---|---|---|
| plasma | line(300) | 23 | 0 | 1 papercut | happy path — vectorizes untouched |
| comet | line(300) | 30 | 2 | 4 friction, 3 papercut | trails + thresholds: densest |
| geq | grid(16×16) | 20 | 1 | 1 friction, 3 papercut | indexing/binning cluster |
| fire | grid(16×32) | 33 | 1 | 4 friction | the stress test — field idiom |
| sdf3d | lattice(10³) | 26 | 1 | 1 papercut | counterweight — arrays shine |

All five: deterministic (double-render byte-identical, seed load-bearing),
zero contract violations over 120 frames, ≤33 author-facing LOC. **Zero
blockers.** Totals: **17 stumbles — 4 hit / 13 shielded; 9 friction / 8
papercut / 0 blocker.** Census reconciles: every `np.where` in pattern code
carries a STUMBLE tag; the kit (`hsv`, `square`) absorbs 3 more branches the
author never saw.

## Stumble inventory

Severity: **blocker** (inexpressible without engine change) · **friction**
(needed a non-obvious idiom) · **papercut** (one-time learning). Locations
are `# STUMBLE-N` comments at the exact line in `bench/authoring/*.py`.

| # | Pattern | Category | Hit? | Sev. | Finding → mitigation |
|---|---|---|---|---|---|
| 1 | plasma | time-parameterization | shielded | papercut | Wrapped 0-1 phase needs integer cycle multipliers inside sin() or it pops at the wrap → document the phase idiom |
| 2 | comet | time-parameterization | shielded | friction | Classic per-frame decay factors (`v *= 0.94`) are frame-rate-dependent; dt forces `exp(-dt/tau)` → ship `fade(dt, tau)` kit helper |
| 3 | comet | branch→where | shielded | papercut | wrap-distance `min()` → `np.minimum` |
| 4 | comet | branch→where | shielded | papercut | `1.0 if d<0.02 else exp(-40d)` → `np.where` — mechanical once seen |
| 5 | comet | branch semantics | shielded | friction | `np.where` evaluates BOTH branches; NaN/domain trap with sqrt/log/div → document + consider a masked `when()` helper |
| 6 | comet | dtype/threshold | **hit** | friction | Carried from bench_throughput kernel B, re-confirmed on this fixture: float32 sin-hash flips 6 pixels vs float64 at the 0.995 threshold → hashes/thresholds near discontinuities must run float64; candidate `hash01()` kit helper hides this |
| 7 | comet | shape assembly | shielded | papercut | scalar `(r,g,b)` tuple → `np.stack(..., axis=1)` + final `astype` after f64 promotion |
| 8 | geq | branch→where | shielded | papercut | per-band peak-hold `if` → `np.maximum` |
| 9 | geq | indexing | **hit** | friction | `int(x*16)` bins IndexError at x==1.0 (verified: unclamped max bin = 16) — every segment pattern needs the edge clamp → ship `bins(x, n)` helper |
| 10 | geq | indexing | shielded | papercut | (16,) state → (N,) per-pixel is a fancy-indexing gather; the scalar spelling happens to be the vectorized spelling |
| 11 | geq | dtype | shielded | papercut | int32 band → float hue needs explicit cast; silent float64 promotion otherwise |
| 12 | fire | reduction/scan | **hit** | friction | **HEADLINE.** Fire2012's neighbor stencil is inexpressible over the unordered `self.pixels` point list. Unblocking idiom: pattern owns an internal heat field, `render` samples it at world coords. Undocumented in ADR-005 → document the internal-field idiom as first-class + ship `sample2d(field, x, y)` |
| 13 | fire | mutation/aliasing | shielded | friction | Classic in-place row-sequential update becomes a simultaneous slice update — silently different (acceptable) diffusion semantics; the sequential spelling cannot be vectorized → document |
| 14 | fire | branch→where + RNG | shielded | friction | Ignition `if random()<p` → mask; RNG only in `before_render`, stable draw shape/order per frame or determinism breaks → engine must teach RNG placement rules |
| 15 | fire | indexing | shielded | friction | World-coord → field-cell sampling boilerplate (scale, round, int cast, edge clamp, 2D gather) repeated by every field pattern → same `sample2d()` helper as #12 |
| 16 | sdf3d | branch→where | shielded | papercut | inside/outside shading `if` → `np.where`; the *only* branch in the pattern — volumetric math is where the surface shines |
| 17 | comet | state-feedback | **hit** | friction | Static additive sparkle fed back through `self.pixels` ratchets to permanent white (fixed point of `min(1, keep·v + 0.3)`). The contract's only per-pixel state is the output buffer itself (render is pure; `before_render` never sees coords), so additive overlays must be transient (time-salted here). Caught by runner statistics, not by eye → decide in Phase 1: sanctioned private per-pixel state buffers alongside `self.pixels` |

## Reading of the evidence

**The scalar illusion holds where it was bet to hold.** Plasma and the 3D
SDF — pure functions of coordinates — are genuinely scalar-looking (1
branch between them, both ≤26 lines) and the SDF is *easier* to write over
arrays than per-pixel. The `np.where` translation itself (the §12 metric)
turned out to be the cheapest stumble class: 5 occurrences, all mechanical
once the pattern is seen (papercuts 3, 4, 8, 16).

**The real friction is not branching.** It clusters in three deeper places
the §12 wording didn't anticipate:

1. **Thresholds + dtype near discontinuities** (#6, #9): float32 coords make
   binning and hash thresholds bite at edges, and nothing warns until the
   rightmost pixel or a flickering spark.
2. **Per-pixel state beyond the output buffer** (#12, #17): stencil effects
   need the internal-field idiom; additive overlays ratchet through
   `self.pixels` feedback. Both were *hit*, both have clean idioms, neither
   idiom is documented in ADR-005.
3. **The time/RNG discipline** (#2, #14): dt-parameterization and
   RNG-placement rules are right but must be taught — they break silently
   otherwise (wrong-speed trails, non-determinism).

**Verdict: GO, conditional on kit additions.** The contract shape
(`before_render`/`render` over arrays + `self.pixels`) survived all five
canonical patterns with zero blockers and ≤33 author-facing lines each.
Freeze the ADR-005 API shape. Before Phase 1 authors arrive, the idiom kit
should grow: `fade(dt, tau)`, `bins(x, n)`, `sample2d(field, x, y)`,
`hash01(x, salt)`, and docs for the internal-field idiom, the
both-branches `np.where` trap, and RNG placement; Phase 1 should also decide
whether private per-pixel state buffers become sanctioned (#17).

## Proposed ADR-005 verification note (pending sign-off — not yet applied)

> ## Verification (Phase-0 item 2, 2026-07-16)
> Prototyped the contract (`bench/authoring/`) and authored the five
> canonical patterns against it: zero blockers, 17 recorded stumbles (4 hit
> / 13 expertise-shielded), all patterns ≤33 author-facing lines,
> deterministic. `np.where` translation proved mechanical; real friction
> is threshold/dtype edges, per-pixel state beyond the output buffer, and
> time/RNG discipline — all mitigable in the idiom kit. Full inventory:
> `bench/results/authoring-2026-07-16.md`. **Status: bet confirmed —
> Accepted**, with the kit additions listed there scheduled before Phase 1
> pattern authoring opens.

## Reproduce

```sh
uv run python bench/bench_authoring.py           # validate + JSON artifact
uv run python bench/bench_authoring.py --show    # ANSI eyeball
```

## Addendum (2026-07-16, post-study)

Building the live preview exposed a latent flaw in `sdf3d.py` that the study
missed: the `spin` parameter is a mathematical no-op — the torus is centered
on the y-axis and `render` rotates about that same axis, which the SDF
(`√(rx²+rz²)`) is invariant under. The pattern animated convincingly anyway
(beat pulse + hue shimmer + the viewer's own camera motion), so nothing
caught it. Worth logging as a stumble-adjacent observation: the vectorized
surface can't flag *semantically* dead parameters, and golden-frame tests
wouldn't either when other motion masks them. The preview's JS port fixes it
with a fixed axis tilt (precession); the Python pattern is left as committed
study evidence.

## Addendum (2026-07-26) — sign-off landed

The proposed verification note above was signed off and applied verbatim as
`## Verification (Phase-0 item 2, 2026-07-16)` in
`research/synthesis/decisions/ADR-005-pattern-authoring-model.md`; the ADR is
now **Accepted (2026-07-26)**. The kit additions the note makes conditional
are scheduled in the Authoring-surface epic of `docs/backlog/v0.2.x.md`,
alongside the param-liveness check this report's addendum motivates. The
"pending sign-off
— not yet applied" heading above is left as written (frozen evidence); this
addendum supersedes it.

## Addendum (2026-07-27) — stumble #17 resolved

The Phase-1 question #17 left open — whether private per-pixel state buffers
become sanctioned alongside `self.pixels` — is decided **yes**. Patterns get a
`setup(n, x, y, z, index)` hook, called once per (pattern, mapping) binding,
and may declare engine-managed persistent buffers there via
`self.buffer(name, shape)`; `render` still receives read-only views, so it stays
pure. Handing `setup` the coordinates is what unbinds #17: per-pixel state can
now be advanced in `before_render` with coordinate knowledge instead of being
laundered through the output buffer, which is what ratcheted the sparkle
overlay to permanent white. Free-form shapes also give #12's internal heat
field a sanctioned home rather than an undocumented idiom. Recorded as
`## Amendment (2026-07-27)` in
`research/synthesis/decisions/ADR-005-pattern-authoring-model.md`; evidence
[S680] (Pixelblaze), [S218] (ISF), [S219] (Shadertoy). Nothing above is
restated or corrected — the inventory stands as measured.

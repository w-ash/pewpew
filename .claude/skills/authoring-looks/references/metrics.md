# Render metrics

What each number in a render's `metrics` means, and how to read it. The
definitions are in `src/pewpew/metrics.py`; this page adds what to do.
Every number is read from the frames as a sink shows them (NaN as 0, above
1 as 1). Luma (Y) is WCAG relative luminance on linear light, 0 to 1. A
fraction is a share of samples (one pixel of one frame) from 0 to 1.

| Metric | What it measures | Read it as |
|---|---|---|
| `frames`, `pixels`, `seconds` | the render's size: frames over fps | under 1 s, flashing cannot be judged (`flash_safe` is unknown) |
| `flash_rate_max` | the most flashes one pixel makes in any one-second window | above 3 fails WCAG 2.3.1 and `verify looks`; fix it first |
| `mean_luma` | average brightness | near 0 is dark; the `mcp-*` looks under `examples/` sit at 0.24 to 0.36 on their own maps |
| `p95_luma` | the 95th percentile of brightness | the highlights; a look with no highlights reads flat |
| `black_fraction` | samples darker than one 8-bit step | 1 is an all-black render, which `verify looks` fails; some black gives contrast |
| `clip_fraction` | samples with a channel at full | a bright layer alone reads high and is fine; when layers add, high values lose detail: lower the opacity or use `screen` in place of `add` |
| `nonfinite` | NaN and infinite values before the sink cleans them | above 0 is a bug in an op |
| `motion_energy` | mean change of a pixel's brightness, per second | near 0 is static; the `mcp-*` looks under `examples/` sit at 0.15 to 0.30 |
| `frozen_fraction` | spans of 0.1 s where nothing moves, at any fps | near 1 means the look is still; check its speed and sync args |
| `spatial_detail` | mean brightness step between neighbouring pixels, in wiring order | low is smooth fields; high is busy texture or noise |
| `palette_spread` | how evenly the colours spread around the hue wheel (OKLab, weighted by chroma; grey counts as no colour) | 0 is one hue, or none; 1 is hues in balance |
| `hue_clusters` | 30° hue bins that hold 5% or more of the coloured samples | how many distinct colour families show |

## Warnings

A render's `warnings` name a gate it would fail (flashing, too short to
judge, all black), a layer that raised (with its node), or frames the
cache could not keep. Read them before the metrics.

## Comparisons

`look_compare` gives `rms` and `max_abs` (the difference of the frames in
linear light), `first_divergent_frame`, `metric_deltas` (B less A, per
metric) and `delta_e_p95` (the 95th percentile of the OKLab colour
difference). These are diagnostics: a large delta says the change shows,
not that it is better.

## Observed engines

`engine_observe` reports the same metrics over the frames a running
engine streams. They are approximate: the frames arrive as 8-bit display
gamma and a large map is decimated, so compare them with each other, not
with an offline render.

# Excerpt provenance

- project: marimapper (https://github.com/TheMariday/marimapper)
- license: GPL-3.0 (project LICENSE is verbatim GPLv3)
- copyright: TheMariday (Mari D) and contributors
- pinned: TheMariday/marimapper@7dc5f799a1b7c180573c2632f6d12a3be0cbf4fa
- excerpted: 2026-07-03 for source [S670]

These excerpts are verbatim copies preserved for research citation
durability (research/README.md archival rule). They are GPLv3-licensed and
MUST NOT be copied into pewpew source code; pewpew may only reimplement the
techniques from the findings doc (research/code-reading/marimapper.md).

## Files

- `detector.py` — from `marimapper/detector.py` L17-L57 (contour_brightness,
  find_led_in_image: THRESH_TOZERO + brightest-integrated-contour +
  sub-pixel moment centroid + width-normalized square coordinates) and
  L123-L186 (find_led, enable_and_find_led: darkness preconditions,
  adaptive-timeout blink detection, off-confirmation). Why: the core
  per-LED detection loop and its robustness gates.
- `database_populator.py` — from `marimapper/database_populator.py`
  L25-L128 (camera model constructors, populate_database). Why: the
  signature trick — synthesizing a COLMAP database with LED IDs as
  pre-matched keypoints and guessed intrinsics.
- `sfm.py` — from `marimapper/sfm.py` L18-L74 (sfm). Why: the loosened
  pycolmap IncrementalPipelineOptions that make sparse LED features
  reconstructable, and largest-submap selection.
- `led.py` — from `marimapper/led.py` L191-L281 (find_inter_led_distance,
  rescale, recenter, fill_gap, fill_gaps). Why: LED-pitch normalization,
  median recentering, and spacing-gated linear gap interpolation.

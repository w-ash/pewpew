# LICENSE NOTE

- project: LedFx (https://github.com/LedFx/LedFx)
- license: GPL-3.0 (LICENSE.txt in repo root)
- copyright: LedFx developers (Austin Hodges et al., per AUTHORS.rst)
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- path: ledfx/effects/audio.py (initialise_analysis constants L1333-L1339; volume_beat_now L1384-L1419; bar_oscillator L1482-L1517; beat_oscillator L1519-L1530)
- why excerpted: the beat feature layer effects actually consume — a cheap
  energy-flux beat detector (low-band sum vs 0.2 s rolling mean, +50%
  threshold, 100 ms refractory) and a phase-interpolated 0..4 bar oscillator
  locked to aubio.tempo, which gives effects a continuous musical phase
  rather than discrete beat booleans.
- reuse caution: GPL-3.0 — reference for reimplementation ideas only; do not
  copy into a non-GPL pewpew codebase verbatim.

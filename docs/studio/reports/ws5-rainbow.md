# WS5: Rainbow gallery pattern

## Built
- `src/pewpew/patterns/rainbow.py`: `Rainbow`, a port of the prototype's rainbow
  (`docs/studio/prototype/golden-tubes-3d.html:336,517`). Hue is
  `d * bands + phase`, where `d` is the distance from (0.5, 0.5, 0.5), through
  `hsv(h, 1, 1)`. `phase` advances by `dt * speed` (mod 1), so a fixed hue moves
  toward smaller `d`: the bands flow inward. Pure, no clock or RNG.
- `src/pewpew/patterns/__init__.py`: exports `Rainbow`; adds
  `(Rainbow, golden-rings mapping)` to `STUDY_CASES`. The mapping is
  `compile_rig(golden-rings.json).mapping` (3072 pixels, read-only, from
  `contain`). `STUDY_CASES` is now built on first access through a module
  `__getattr__` and cached, so importing `pewpew.patterns` does not import the rig
  (pydantic, about 85 ms measured). `from pewpew.patterns import STUDY_CASES` still works.
- `tests/test_port_equivalence.py`: pairs study classes with the first five
  `STUDY_CASES` entries only, since Rainbow has no study prototype.
- `tests/goldens/rainbow.npz`: new, the only golden changed.

## Defaults
- `bands = 3.9`, range 0.5 to 12. The prototype has one spectrum per 100 cm
  (`uWave = L`, tube length 1 m). The golden rings are about 3.87 m wide, so
  3.87 / 1.0 is about 3.9 spectra per normalized unit. Inference, labelled as such in the code.
- `speed = 0.25`, range 0 to 2. The prototype sets `uTime = now / 4000` (ms), which is 0.25 cycles/s.

## Checks
- `uv run pytest`: 318 passed, 2 xfailed (existing), about 2.4 s.
- Liveness: `rainbow-bands` and `rainbow-speed` pass, static and while running.
- `python -m pewpew run rainbow --ansi --frames 30` exits 0.

## Open
- The prototype takes distance from the world origin at full size. The port uses
  the Contain-normalized center. Both are the piece's center on the golden rings,
  but they differ on a rig whose bounding box is off-center.
- The prototype clamps color to the tube axis (`vWorld` at `transformed.y` clamped), so
  one tube end takes one color. The port colors each pixel at its own position.
- The default `bands` assumes a rig about 3.87 m wide. On a smaller rig the
  spectrum count per meter changes; the user adjusts `bands`.

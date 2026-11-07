# Code review of the ws5 Rainbow pattern (high effort)

- **Reviewer:** an independent agent (Opus), not the author. It ran the `code-review` skill at
  high effort and dropped two skill findings it could not back up.
- **Target:** `git diff studio...studio-ws5-rainbow`, on 2026-10-22.
- **Verdict:** no correctness bug in the pattern itself.
- **Fixes:** the fix pass records what it did with each finding in `ws5-fixes.md`.

## Findings, most severe first

**1. Every gallery run now compiles the golden rig.** CONFIRMED, medium
- **Where:** `src/pewpew/patterns/__init__.py:69,75`, with `src/pewpew/load.py:237-240`.
- **Defect:** `load._gallery` calls `getattr` on every name in `__all__`, `STUDY_CASES`
  included. `default_mapping` always calls `_study_cases()`. So every `run <name>` imports
  pydantic and `pewpew.rig` and compiles the golden rings, even `run plasma --map line:8`.
- **Scenario:** a bad edit to the catalog or to `golden-rings.json` makes
  `run plasma --map line:8` die with a `RigError` traceback. `functools.cache` doesn't cache
  exceptions, so every later access compiles again.
- **Fix:** have `_gallery` iterate a `PATTERNS` tuple, or filter names before calling `getattr`.
  Make `default_mapping` look up a per-class cached builder, so only `run rainbow` touches the
  rig.

**2. The port-equivalence pairing no longer catches a missing study class.** CONFIRMED, low
- **Where:** `tests/test_port_equivalence.py:51`.
- **Defect:** the slice `STUDY_CASES[: len(STUDY_CLASSES)]` pairs by position only.
- **Fix:** pair by class with a dict, and assert that every gallery class is either study-backed
  or listed in an explicit `NO_STUDY = {Rainbow}`.

**3. The `bands` default is about 2% high.** CONFIRMED, low
- **Where:** `src/pewpew/patterns/rainbow.py:14-16`.
- **Defect:** the default of 3.9 uses the prototype's tube-end width (386.6 cm). Contain's unit
  is the extent of the pixel centers, 3.8313 m measured from `compile_rig(...).positions_m`.
- **Fix:** set the default to 3.83 and correct the comment.

**4. `run rainbow`'s default map is not tested through the runner.** CONFIRMED, low
- **Where:** `tests/test_runner.py:48`.
- **Fix:** add a `("rainbow", 3072)` case.

**5. Several docstrings and comments still describe five study ports.** CONFIRMED, low
- **Where:**
  - `src/pewpew/patterns/__init__.py:1-3, 22-23`
  - `tests/test_engine_goldens.py:1`
  - `tests/test_param_liveness.py:57`: "nine today"; there are now 11 cases.
- **Fix:** update the text.

**6. `dir()` and `inspect` can't see `STUDY_CASES`.** CONFIRMED, nit
- **Where:** `src/pewpew/patterns/__init__.py:57-62`.
- **Fix:** add a `__dir__` that includes `STUDY_CASES`.

**7. Two calls are redundant.** CONFIRMED, nit
- **Defect:** `@functools.cache` on `_golden_rings` does nothing, and neither does `_frozen` on
  an already read-only mapping.
- **Status:** the simplify pass (`ws5-simplify.md`) already removed both.

## Checked and sound

- **Inward flow:** proved numerically, with an error of 2.9e-7, and the hue direction matches
  the prototype.
- **Float drift:** the phase stays exact over 24 h at 60 fps.
- **Determinism:** the pattern is deterministic.
- **Liveness:** both knobs pass, with RMS 0.657 and 0.624 against the 1e-3 bar.
- **Lazy `STUDY_CASES`:** imports, pickling, hot reload and `default_mapping` all work.
- **Mapping and ports:** the golden-rings mapping is read-only, and all five study ports still
  pass.

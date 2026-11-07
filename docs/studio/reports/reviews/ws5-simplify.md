# WS5 simplify pass

Scope: `git diff studio...HEAD` (rainbow.py, patterns/__init__.py, test_port_equivalence.py).
Review ran inline (four angles: reuse, simplification, efficiency, altitude); the diff was too small for separate agents.

## Changed
- `src/pewpew/patterns/__init__.py:36-50`: removed `_golden_rings()` and folded it into `_study_cases()`.
  Its `functools.cache` was redundant (sole caller is itself cached), and its `_frozen(...)` call did nothing:
  `contain` (`src/pewpew/rig/compile.py:99`) already returns a read-only array.
  The rig-import comment now sits at the import.
- `src/pewpew/patterns/__init__.py:54`: shortened the `__getattr__` comment to point at `_study_cases`.

## Left alone
- `rainbow.py`: no duplication, no waste; comments explain non-obvious choices (inference for `bands`, phase sign).
- Lazy `STUDY_CASES` via module `__getattr__`: keeps `from pewpew.patterns import STUDY_CASES` working and avoids the pydantic import at package import. Kept.
- `tests/test_port_equivalence.py:51`: the `[: len(STUDY_CLASSES)]` slice with `strict=True` is the simplest way to skip Rainbow; kept.
- `tests/goldens/rainbow.npz`: untouched; matches without regeneration.

# ws1 rig core: simplify pass

Four review angles (reuse, simplification, efficiency, altitude) over `git diff studio...HEAD` for the rig code. Schemas regenerated: diff empty. `uv run pytest`: 311 passed, 2 xfailed, about 3 s.

## Changes

| Where | Change | Reason |
|---|---|---|
| `src/pewpew/rig/models.py:636-642` | Added `Issue.of(level, code, message, ref)` and `Issue.error(code, message, ref)` | Four hand-written copies of the same constructor (`_error` x3, `_issue`); `_issue` also typed `level` as `str`. Classmethods do not touch the schema. |
| `src/pewpew/rig/catalog.py`, `compile.py`, `migrate.py` | Deleted the local `_error` / `_issue`; call sites use `Issue.error` / `Issue.of` | Same. |
| `src/pewpew/rig/__init__.py:55`, `wiring.py:25`, `compile.py` (`_explicit_plan`) | Inline `Issue(level=..., ...)` now use the classmethods | Same. |
| `src/pewpew/rig/compile.py:~47` | Removed the `MAX_FIXTURES` re-check in `compile_rig` and its import | `Arrangement._size` already enforces it on a frozen model; the one test goes through `load_arrangement`. |
| `src/pewpew/rig/compile.py:~96` | Dropped `report=None` | Already the field default. |
| `src/pewpew/rig/catalog.py:~217` | Removed `Catalog.entity_digest` | No caller in src, tests, scripts or the contracts API. |
| `src/pewpew/rig/catalog.py:~137-150` | Removed `chipsets`, `connectors`, `firmware` properties and unused `Chipset`/`Connector` imports | Only one test read them; `of_kind(kind)` serves. `tests/test_rig_catalog.py:42-46` updated. |
| `src/pewpew/rig/catalog.py:~247-262` | `_fact` builds on `_text` | The status/src lines were duplicated. |

## Considered and left alone

- `Catalog.to_json` / `of_kind` caching, `describe_presets` caching, per-group attach check hoisting, per-chain set rebuilds (efficiency): fleet cap is 200 fixtures, so the saving is small; caching adds invalidation and mutability risk.
- `migrate` skipping `deepcopy` when no step runs: the returned dict would share nested objects with the input, which changes the "new dict" contract.
- `Expr` validator replacing the `_*_numbers` walkers (altitude 1): changes the `bad_expression` code and ref for syntax errors.
- Presets registry, moving `_explicit_plan` into `wiring.py` (altitude 2, 3): WS2 is rewriting `auto_wire`; refactoring now would conflict.
- Moving intra-entity catalog checks onto models (altitude 6): issue `ref` strings change.
- Typed `get`/`has`, derived `KINDS`, typed `CompiledRig.report` (altitude 7, 8): API-adjacent; the report type does not exist yet.
- `FixtureSpec.reset_s`, and the `pose.py` helpers `to_mvr`, `from_mvr`, `matrix_to_quat`, `rot_x`, `rot_z`, `from_three`: used only by tests, but `domain-model.md` plans them.
- Shared `+ 0.0` helper for negative-zero normalisation (`models.py:390`, `pose.py:130,151`): cosmetic.

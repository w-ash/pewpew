# Code review of the ws1 rig core (high effort)

- **Reviewer:** an independent agent (Opus), not the author. It ran the `code-review` skill at
  high effort and read the author's report only after its own review.
- **Target:** `git diff studio...studio-ws1-rig` at `db1fe9e`, on 2026-10-22.
- **Verdict:** no geometry errors. 13 verified defects, the worst at the public boundary.
- **Fixes:** the fix pass records what it did with each finding in `ws1-fixes.md`.

## Findings, most severe first

**1. `load_arrangement` reads any string as a file path.** CONFIRMED; the studio impact is
PLAUSIBLE.
- **Where:** `src/pewpew/rig/__init__.py:51`.
- **Defect:** any string that does not start with `{` becomes `Path(obj).read_text()`.
- **Scenario:**
  - `load_arrangement("/etc/hosts")` read the file.
  - `"[1]"` and `"null"` raise a raw `FileNotFoundError`, and `"/tmp"` raises
    `IsADirectoryError`; none of them is a `RigError`.
  - If the studio passed body text, a client would get a file-existence oracle.
- **Fix:** always parse a `str` as JSON text, take paths only as `os.PathLike`, and turn
  `OSError` into a `RigError`. The contract is now pinned this way (contracts.md).

**2. Deep nesting crashes migration.** CONFIRMED
- **Where:** `src/pewpew/rig/migrate.py:38`.
- **Defect:** `copy.deepcopy` runs before validation.
- **Scenario:** about 500 levels of nesting in any field (about 1 KB of JSON) raises
  `RecursionError` out of `load_arrangement`, which surfaces as a 500, not a 422.
- **Fix:** skip the copy while `STEPS` is empty or copy only the known keys, validate first, and
  turn `RecursionError` into a `RigError`.

**3. Unbounded magnitudes reach the mapping.** CONFIRMED
- **Where:** `src/pewpew/rig/models.py:414, 471, 501`; `src/pewpew/rig/compile.py:116-123, 449`.
- **Scenario:**
  - Fixtures at x = ±1.7e308, or a ring with radius 1e308, make `contain` overflow, so
    `rig.mapping` holds NaN.
  - An array with step 1e308 puts inf in a matrix, and a raw pydantic `ValidationError` escapes
    `compile_rig`.
- **Fix:** bound the lengths in the models (|position| ≤ 1e4 m, 0 ≤ `start_radius_m` ≤ 1e3,
  |step| ≤ 1e3), and check in `compile_rig` that positions and matrices are finite.

**4. Quaternion canonicalization is not idempotent.** CONFIRMED
- **Where:** `src/pewpew/rig/models.py:386`.
- **Defect:** every load renormalizes again.
- **Scenario:** saving after a load changes the stored value for 131 of 5,000 random unit
  quaternions, and some oscillate by an ulp. Share ids hash the canonical JSON, so re-saving an
  unedited arrangement can produce a new id.
- **Fix:** return q unchanged when |‖q‖ − 1| is within a few ulp, and add a test that
  save → load → save is idempotent.

**5. The aim axis is checked only for exact zero.** CONFIRMED
- **Where:** `src/pewpew/rig/models.py:399-404`, `src/pewpew/rig/pose.py:92-103`.
- **Scenario:**
  - `[1e-200,0,0]` underflows the norm, and a raw `ValueError` escapes.
  - `[1e200,1e200,0]` overflows it, giving a rotation with det 0 that collapses all 64 pixels
    into one point, with no issue raised.
- **Fix:** scale by max|component| before taking the norm, or bound |axis|, and raise `bad_aim`.

**6. Only fixtures are capped.** CONFIRMED
- **Where:** `src/pewpew/rig/models.py:543, 588-589, 611-614`.
- **Defect:** `chains`, `feeds`, `controllers`, `psus` and `chain.fixtures` are unbounded lists.
- **Scenario:** an 8 MB body with one chain of 10⁶ unknown ids takes 1.15 s and builds 1,000,001
  issues.
- **Fix:** set `max_length` on those lists, and truncate the issue list (the first 100 plus a
  count).

**7. Some errors escape the expression evaluator.** CONFIRMED
- **Where:** `src/pewpew/rig/expr.py:60-71, 85-114`; `src/pewpew/rig/catalog.py:388, 422`.
- **Defect:** `OverflowError`, `RecursionError` and `MemoryError` escape, because only
  `ExprError` is caught.
- **Scenario:** `"1"+"0"*400`, `"-"*5000+"1"` and a chain of 5,000 dims each crash
  `load_catalog`. Today only the bundled catalog reaches this path.
- **Fix:** cap the source length and AST depth in `parse`, and turn those errors into
  `ExprError`.

**8. Catalog checks miss zero values.** CONFIRMED, bundled data only
- **Where:** `src/pewpew/rig/catalog.py:400-413`.
- **Defect:** an anchor `dir` of zero, a zero `facing`, `v_nominal` 0 and `span_m` ≤ 0 all load.
- **Scenario:** a zero `end_b.dir` makes `compile_rig` raise. A `v_nominal` of 0 makes
  `Catalog.to_json()` raise `ZeroDivisionError`, which would break `GET /api/catalog`.
- **Fix:** validate these as nonzero or positive.

**9. Validation coerces types loosely.** CONFIRMED
- **Where:** `src/pewpew/rig/__init__.py:58`.
- **Defect:** lax mode accepts `"count": true` as 1, `"count": "3"` as 3, and string numbers in
  positions.
- **Fix:** validate in strict mode.

**10. `run --map file.json` crashes on some files.** CONFIRMED
- **Where:** `src/pewpew/__main__.py:92-99`.
- **Scenario:** a directory named `*.json` gives an `IsADirectoryError` traceback. An empty
  arrangement compiles to n = 0 and then crashes the ANSI sink at `np.ptp`
  (`src/pewpew/sinks/ansi.py:74`).
- **Fix:** catch `OSError` and `UnicodeDecodeError`, and refuse `rig.n == 0`.

**11. The `RingGroup` docstring is wrong.** CONFIRMED
- **Where:** `src/pewpew/rig/models.py:459`.
- **Defect:** it says the inner end sits at `start_radius_m`. It is the flat (untilted)
  inner-end radius, and the member tilts about its midpoint at r₀ + L/2. `describe_presets`
  sends this docstring to the UI.
- **Fix:** correct the docstring.

**12. A misleading error message.** CONFIRMED
- **Where:** `src/pewpew/rig/compile.py:296-300`.
- **Defect:** a fixture listed twice in one chain is reported as "in chain A and chain A".
- **Fix:** give it its own `duplicate_in_chain` code.

**13. `Wiring.target_fps` is never read.** CONFIRMED
- **Where:** `src/pewpew/rig/models.py:587`.
- **Fix:** ws2's report reads it, so the "wire fps below target" warning can fire.

## Checked and sound

- **Ring basis.** It matches the prototype's `makeBasis(side, dir, side×dir)`, including
  `data_in: "outer"` and the tilt sign, to 1e-12 on all 48 members.
- **Quaternions.** `matrix_to_quat` follows three.js branch for branch, with w ≥ 0. The round trip
  holds, including the 180° cases. Output is column-major.
- **Pixels.** Pixel placement and the 1/64 pitch are exact, and normals are R·facing.
- **Contain.** It is correct and centered.
- **MVR.** The conversion round-trips. Reading u, v and w as columns is an inference supported by
  GDTF's matrix layout
  (https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md#L201).
- **Data order.** It runs controller, output, chain, pixel, with unwired fixtures last, and the
  `pixel_start` and `pixel_count` tables agree.
- **Expression safety.** Attribute access, calls, subscripts, lambdas, comprehensions, `**` and
  comparisons are all refused, nothing calls `eval`, and cycle detection works.
- **Validation.** The 200-fixture cap applies before expansion. `extra="forbid"` is on all 13
  arrangement models. NaN and Infinity are refused, and issue messages carry no paths.
- **Catalog data.** INV-001 and INV-002 match the maintainer's fixture notes
  (INV-001, INV-002, RES-011, RES-012, RES-038) and the design.
- **Determinism.** Two compiles give byte-identical arrays, and there is no clock or RNG.
- **Tests.** The golden-rings test checks the prototype's own figures (386.6 and 403.9 cm).

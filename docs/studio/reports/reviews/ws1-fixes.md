# Fixes for the ws1 code review

The fix pass for [`ws1-code-review.md`](ws1-code-review.md), on branch `studio-ws1-fix`. Tests are in
`tests/test_rig_boundary.py` unless named otherwise. Each new test fails on `studio` and passes
here, except two guards that pass on both: a 500 m arrangement compiles, and 300 nested
parentheses are refused.

## Per finding

1. **Fixed.** A `str` is always JSON text, and only an `os.PathLike` is read as a file. `OSError`,
   undecodable text and a null byte in the path become `unreadable_file` or `bad_json`, with no path
   in the message (`src/pewpew/rig/__init__.py:52`, `:75`). The docstring example now passes a
   `Path` (`__init__.py:5`). `__main__._rig_mapping` already passes a `Path`. `pewpew.patterns`
   never calls `load_arrangement` (not found by `rg`). Tests: `test_a_string_is_always_json_text_never_a_path`
   and `test_an_unreadable_file_is_a_rig_error`.
2. **Fixed.** At the latest version `migrate` makes a shallow copy. It deep-copies only when a step
   runs, and turns `RecursionError` into `too_deep` (`src/pewpew/rig/migrate.py:45-48`).
   `load_arrangement` also catches `RecursionError` from `json.loads` and `json.dumps`, and pydantic's
   JSON parser refuses deep input as `json_invalid`. Tests: `test_deep_nesting_is_a_rig_error` and
   `test_a_migration_step_on_deep_input_is_a_rig_error`.
3. **Fixed.** These limits are the review's. |position| ≤ 1e4 m holds for poses, controllers and
   PSUs (`src/pewpew/rig/models.py:408`). `start_radius_m` is between 0 and 1e3 (`models.py:501`),
   and each array step component has |step| ≤ 1e3 (`models.py:531`). `compile_rig` refuses a
   non-finite world matrix and a non-finite mapping with `not_finite` (`src/pewpew/rig/compile.py:209`,
   `:84`). Tests: `test_out_of_range_lengths_are_refused_on_load`,
   `test_an_arrangement_hundreds_of_meters_across_compiles` and
   `test_compile_refuses_positions_it_cannot_normalize`.
4. **Fixed.** `canonical_quat` does not divide again when |‖q‖ − 1| ≤ 4 ε (`models.py:399`). Of
   100,000 seeded random quaternions, none changed on a second pass. Tests:
   `test_canonical_quat_is_idempotent`, and `test_save_load_save_is_idempotent`, which covers golden
   rings and 200 random quaternions.
5. **Fixed.** `pose.unit` divides by max|component| before it takes the norm
   (`src/pewpew/rig/pose.py:85`). `aim` and `anchor_frame` use it (`pose.py:106`, `:178`). Any
   nonzero finite axis now gives a proper rotation, and the model still refuses a zero axis as
   `bad_aim`. Test: `test_aim_takes_the_direction_of_any_finite_axis`.
6. **Fixed.** `Capped` holds at most `MAX_FIXTURES` (200) items (`models.py:414`). It applies to
   `chains`, `feeds`, `controllers`, `psus`, `groups` and `fixtures`, and `chain.fixtures` has the
   same cap (`models.py:573`). The review did not list `groups` and `fixtures`: 10⁶ free fixtures
   took 1.8 s to refuse, and now take 0.66 s. Over 100 issues, `RigError` keeps the first 100,
   errors first, plus one `too_many_issues` count (`models.py:686-690`). Tests:
   `test_every_arrangement_list_is_capped` and `test_a_rig_error_keeps_the_first_issues_errors_first`.
7. **Fixed.** `parse` refuses source over 256 characters, a tree deeper than 64 and a literal too
   large for a float. It turns `RecursionError` and `MemoryError` from `ast.parse` into `ExprError`
   (`src/pewpew/rig/expr.py:26-57`). `evaluate` maps `OverflowError`, and `resolve` refuses a dims
   chain over 64 (`expr.py:125`). `read_catalog` turns unreadable, non-UTF-8 and deeply nested
   files, and a missing root, into issues (`src/pewpew/rig/catalog.py:534-555`). Tests:
   `test_expressions_out_of_range_are_expr_errors`, `test_long_dims_chains_are_expr_errors`,
   `test_a_bad_expression_in_the_catalog_is_a_rig_error` and `test_an_unreadable_catalog_is_a_rig_error`.
8. **Fixed.** A zero anchor `dir`, a zero `pixels.facing`, `span_m` ≤ 0 and `v_nominal` ≤ 0 are
   `bad_value` errors (`catalog.py:385-401`). Test: `test_catalog_refuses_zero_directions_and_values`.
9. **Fixed.** `load_arrangement` validates with `model_validate_json(..., strict=True)`
   (`__init__.py:70`). In Python mode, strict validation refuses a list for a tuple, so the data goes
   through JSON mode. A JSON integer is still a valid float. Tests: `test_counts_must_be_integers`
   and `test_positions_must_be_numbers`.
10. **Fixed.** Because of fix 1, a directory, a missing file and a non-UTF-8 file each reach
    `_rig_mapping` as a `RigError`, which it already turns into a clean exit (`src/pewpew/__main__.py:93`).
    An extra `OSError` catch would never run, so I did not add one. `rig.n == 0` is refused
    (`__main__.py:99`). Test: `tests/test_runner.py::test_run_reports_an_unreadable_or_empty_arrangement`.
11. **Fixed.** The docstring now puts the midpoint at `start_radius_m + L/2` and gives the tilted
    inner end's plan radius (`models.py:485`). The regenerated schema carries the new text. Test:
    `test_ring_docstring_matches_the_geometry`.
12. **Fixed.** A fixture listed twice in one chain is `duplicate_in_chain` (`compile.py:296`).
    `wiring.py` is unchanged. Test: `test_a_fixture_listed_twice_in_one_chain_has_its_own_code`.
13. **Comment only, as briefed.** `models.py:617-619` notes that ws2's electrical report reads
    `target_fps`. There is no test, because nothing changes behavior.

## Checks

- `schemas/arrangement.v1.json` was regenerated with `scripts/export_schemas.py` and changed only
  for the bounds, the caps and two docstrings. `catalog.v1.json` did not change.
- Golden rings is unchanged. A SHA-256 over `mapping`, `positions_m`, `normals`, `fixture_of`,
  `pixel_in_fixture` and `to_json()` is identical before and after, for golden rings and for the
  ring-and-tube example. The existing dimension tests pass.
- `uv run --all-extras --all-groups pytest`: 346 passed, 2 xfailed, in 2.5 s.

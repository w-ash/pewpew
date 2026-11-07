# Fixes for the ws3 code review

- **Review:** `docs/studio/reports/reviews/ws3-code-review.md` (13 findings).
- **Branch:** `studio-ws3-simplify`, after merging `studio` (the rig core and the pinned contracts)
  and `studio-ws1b-geometry` (`pewpew.rig.geometry`).
- **Tests:** all in `tests/test_studio.py`. `uv run pytest` passes: 403 passed, 2 xfailed, about 5 s.

## Findings

1. **Fixed.** Changes are coalesced: one bind slot, one pattern slot and a sets dict, applied by at
   most one queued closure (`src/pewpew/studio/session.py:250` `_pending`, `:262` `_apply_pending`).
   A pattern change drops the pending sets that were checked against the old pattern. Tests:
   `test_pending_changes_coalesce_into_one_closure`,
   `test_a_pattern_change_drops_sets_checked_against_the_old_pattern`.
2. **Fixed.** A paused or idle session closes after `PAUSED_TIMEOUT_S` (30 min) and frees its slot
   (`src/pewpew/studio/app.py:452`). At the cap, `Admission.acquire` evicts the session paused
   longest (`src/pewpew/studio/limits.py:122`, `src/pewpew/studio/session.py:332`). Per-address
   limits key IPv6 by /64 (`src/pewpew/studio/limits.py:56` `address_key`). Tests:
   `test_a_paused_session_closes_after_the_paused_deadline`, `test_an_idle_session_pauses_then_closes`,
   `test_a_full_server_evicts_the_session_paused_longest`,
   `test_a_full_server_with_no_paused_session_still_refuses`, `test_ipv6_addresses_count_per_64`.
3. **Fixed.** `declared_fixtures` counts `fixtures` plus each group's `count` or `counts` product
   from the raw JSON, before compiling, and stops counting past the cap
   (`src/pewpew/studio/limits.py:74`, used at `src/pewpew/studio/app.py:244`). The rig's own cap in
   `load_arrangement` also refuses before `expand` runs, as `{"issues"}`. `rig.n` is capped at
   `MAX_PIXELS` = 16,384 (`src/pewpew/studio/app.py:258`). Tests:
   `test_group_sizes_count_toward_the_fixture_cap_before_compiling`,
   `test_an_arrangement_at_the_fixture_cap_compiles`,
   `test_real_rig_refuses_a_huge_group_before_expanding`, `test_pixel_cap`.
4. **Fixed.** The message check counts UTF-8 bytes (`src/pewpew/studio/app.py:473`). The transport
   cap still comes only from `python -m pewpew studio`, which contracts.md pins as the production
   launch. Test: `test_message_size_is_counted_in_bytes`.
5. **Fixed.** Compiles take a token from a per-address bucket (60 a minute, burst 10; 429) and one
   of 2 global slots, waiting up to 5 s (503) (`src/pewpew/studio/app.py:246-249`). A bind reads
   `rig.issues` in the worker thread and never calls `to_json` (`src/pewpew/studio/app.py:269`).
   `/api/compile` serializes in the threadpool (`src/pewpew/studio/app.py:332`). Tests:
   `test_compile_rate_limit_per_address`, `test_concurrent_compiles_are_bounded`,
   `test_bind_takes_issues_from_the_rig_and_never_serializes_it`.
6. **Fixed.** `BodyLimit` sends the 413 itself, gives the app a disconnect and drops the app's
   reply (`src/pewpew/studio/limits.py:208`). Test: `test_a_chunked_body_over_the_limit_is_413`.
7. **Fixed.** `RateLimiter` is a token bucket in an `OrderedDict` in last-use order. Idle keys
   leave from the old end in O(1) amortized time, with a hard cap of 10,000 keys
   (`src/pewpew/studio/limits.py:161`). It replaces `SaveLimiter`. Test:
   `test_rate_limiter_table_is_bounded_and_drops_idle_keys`.
8. **Fixed.** `openapi.json` is regenerated. Every 422 in it is now `IssueList`. Test:
   `test_committed_openapi_matches_the_app`.
9. **Fixed.** A queued hello clears the pending frame (`src/pewpew/studio/transport.py:75`). Test:
   `test_a_hello_drops_the_frame_queued_before_it`.
10. **Fixed.** `Outbox`, `Session` and `registry.add` run inside the `try`, and `Admission.release`
    is idempotent per `Ticket` (`src/pewpew/studio/app.py:386-395`). Test:
    `test_a_session_that_fails_to_start_releases_its_slot`.
11. **Fixed.** `ParamSet.check` catches `OverflowError` (`src/pewpew/pattern.py:265`). An
    unexpected compile error during a bind becomes `refused` and is logged at WARNING
    (`src/pewpew/studio/app.py:526`). Tests:
    `test_param_check_refuses_an_integer_too_large_for_a_float`,
    `test_a_huge_integer_set_is_refused_and_the_socket_stays_open`,
    `test_an_unexpected_compile_error_is_refused_and_logged`.
12. **Fixed.** A `RequestValidationError` handler returns `{"issues"}`, and so does FastAPI's 400
    for a body its JSON parser gave up on (too deep, or bad UTF-8)
    (`src/pewpew/studio/app.py:298`, `:310`). `/api/catalog` uses `Catalog.to_json()`, and power
    comes from `CompiledRig.estimate_effect_power`, as pinned. Test: `test_every_422_carries_issues`.
13. **Partly fixed.** The catalog body and each type's digest and GLB bytes are built once per
    catalog, on first use (`src/pewpew/studio/app.py:152` `_CatalogView`). The GLB route only looks
    the digest up, so an unknown digest gets 404 with no rebuild (`:339`). Tests:
    `test_the_digest_map_is_built_once_and_unknown_assemblies_rebuild_nothing`,
    `test_real_geometry_serves_every_assembly_once_built`.
    **Skipped:** a rate limit on GETs and pooled Postgres connections. The brief kept only the cheap
    parts. A malformed id still never reaches the database, but a well-formed unknown id opens one
    connection.

## Other work from the brief

- **Real rig.** `create_app()` defaults to `pewpew.rig.load_catalog` and `compile_rig`.
  `pewpew.rig.geometry` is imported on first use (`src/pewpew/studio/app.py:144`). If the module
  or manifold3d is missing, catalog entries carry `"digest": null, "assembly_url": null` and the
  GLB route answers 503 (`:167`, `:337`). Under uvicorn, the first `/api/catalog` built all four
  assemblies in 36 ms. Later requests were served from memory. Power uses
  `rig.estimate_effect_power` behind a `hasattr` guard until ws2 adds it. Tests:
  `test_real_rig_compiles_and_binds_golden_rings` (n = 3072, frame = 8 + 3·3072 bytes),
  `test_missing_geometry_gives_503_and_no_assembly_urls` (module missing, manifold3d missing).
- **Input safety (coordinator note).** `compile_checked` passes only a dict to the rig, so a
  client string never reaches `Path(...)`. Around the compile it catches `ValueError` (which covers
  `RigError` and `ValidationError`), `RecursionError` and `OverflowError`, and returns them as
  `{"issues"}` or `refused`. The catch stays until `studio-ws1-fix` merges. Tests:
  `test_only_dicts_reach_the_rig`, `test_real_rig_errors_are_422_issues_never_500`.
- **Duplicate removed.** `pewpew.load.gallery_patterns()` is now public, and `_gallery` and the
  studio both use it (`src/pewpew/load.py:230`).

## Still open

- ws4 must regenerate its orval client: 5 of the 6 operationIds changed with the regenerated
  `openapi.json`.
- ws4 must accept a null `assembly_url`, which a server without manifold3d sends.

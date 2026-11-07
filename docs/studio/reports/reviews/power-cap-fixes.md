# Power cap: review fixes

These are the fixes for [`power-cap-code-review.md`](power-cap-code-review.md) (8 findings), made
after the simplify pass ([`power-cap-simplify.md`](power-cap-simplify.md)). The review's line
numbers are at `d5b81d6`. The same commit also carries the coordinator's later additions: the
auto-white worst case, feed checks at the capped current, the BTF brick and the four-brick
examples ([`../power-cap.md`](../power-cap.md)).

## Per finding

1. **Fixed.** A frame that fails in `Session._on_frame` is now dropped, and the limiter stays bound,
   so a failure never streams uncapped light. The first exception of each type is logged, so a
   fault that repeats every frame does not flood the log. Test:
   `test_a_failed_frame_is_dropped_and_the_cap_stays_bound` makes `sink.frame` raise once under
   `max_brightness` 0 and checks that the next frames are still black.
2. **Kept, with the ADR made exact.** The per-supply rule stays. One global scale lets a frame that
   lights one supply's fixtures put more on that supply than the report sized it for: at 500 W,
   332.8 W on a supply sized for 270.8 W. The ADR amendment's "Two limits" item now states the
   per-supply rule and the `(max_watts − flat) / variable` form. The maintainer has not yet confirmed
   the rule, so it stays on the project's list of open decisions, which is not in this repo.
3. **Fixed.** An uncapped limiter runs only when a power reading is due, every
   `round(fps / POWER_HZ)` frames. A capping limiter still runs on every frame. Test:
   `test_an_uncapped_limiter_runs_only_when_a_reading_is_due`.
4. **Fixed.** A PSU whose every-channel load is over its rating, while its RGB load is within it,
   gets the warning `psu_full_white_overload`. The warning names both currents and says that a
   fallback preset overloads the PSU. The warning is not raised when the RGB load is itself over the
   rating, because `psu_overload` already covers that case. Test:
   `test_a_psu_that_only_the_cap_keeps_in_rating_is_flagged` uses the review's
   `max_brightness: 0` case. Since PSUs are now sized for the RGB worst case, the uncapped golden
   rings warn on p1 and p2 too (21.3 A against 14.6 A each).
5. **Message fixed.** The error now reads "--max-watts needs --map with an arrangement .json, whose
   fixtures give the power model". A gallery default map is still not compiled into a rig: the
   default path keeps only a mapping (`pewpew.patterns.default_mapping`), and `--map` with the
   rings file is one flag away.
6. **Fixed.** `MAX_CAP_W` moved to `src/pewpew/power.py`. `PowerCap` refuses a `max_watts` over it,
   so the CLI and the file format take the same range, and `pewpew.rig.models` imports the
   constant. Test: the `5e9` and NaN cases in `test_cap_refuses_values_out_of_range`.
7. **Fixed.** A closed socket resets `uncappedWatts` with `watts`. The reconnect test in
   `web/src/session/client.test.ts` now asserts both.
8. **Fixed.** `docs/studio/reports/power-cap.md` is committed with this work.

## From the unverified list

- **`limit_stage` can raise inside `PacedLoop`.** Fixed. A frame the limiter refuses is dropped and
  logged once per exception type, never sent uncapped. Test:
  `test_limit_stage_drops_a_frame_the_limiter_refuses`.
- **The `app.py` comment.** Fixed: "A rig without a limiter streams uncapped, with no power
  messages."
- **Commits on each keystroke.** Not changed. The review found it mostly mitigated: compile and bind
  are debounced, and undo coalesces on the key `"power"`.
- **Sizing and budgets computed separately.** Not changed. They agree, and
  `test_golden_rings_supplies_keep_within_their_capped_report_loads` checks the limiter against the
  report's PSU loads.
- **`is_flat` lookups.** Not changed. The review measured no cost.

## Gates

- `uv run --all-extras --all-groups pytest`: 575 passed, 2 xfailed.
- `web/`: `pnpm check` passed. `pnpm test` passed 79 of 79. `pnpm e2e` passed 4 of 4.

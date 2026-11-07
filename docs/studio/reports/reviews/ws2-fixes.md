# Fixes for the ws2 code review

The fix pass for [`ws2-code-review.md`](ws2-code-review.md), on branch `studio-ws2-review`, after the
simplify pass ([`ws2-simplify.md`](ws2-simplify.md)). Tests are in `tests/test_rig_wiring.py` (W) and
`tests/test_rig_electrical.py` (E). Each new test fails on the simplify commit `f38db41` and passes
here, except two that pass on both: the finding 14 refactor test, and
`test_the_report_is_finite_at_every_bound`, which guards the new bounds. `uv run --all-extras
--all-groups pytest`: 412 passed, 2 xfailed.

## Per finding

1. **Fixed.** Auto-wiring now picks the PSU first and grows the feed against that PSU's position, so the drop is checked for the PSU the feed is on (`src/pewpew/rig/wiring.py:316-341`, `:346-382`). Test: W `test_a_feed_is_sized_for_the_psu_it_is_on`.
2. **Fixed.** `target_fps` ≥ 0.1, `hop_slack` ≤ 10, each fraction ≥ 0.01, and `Feed.length_m` ≤ 1e9 m (`src/pewpew/rig/models.py:49-58`, `:649`, `:669-675`, `:684`). The cable bound sits far over the longest auto feed (under 1e7 m), because array members can lie about 3.7e5 m from the origin. Tests: E `test_options_that_overflow_the_arithmetic_are_refused`, and E `test_the_report_is_finite_at_every_bound`, whose widest case has an auto feed over 1e6 m.
3. **Fixed.** `feed_overlap` is one issue per feed, naming the feeds it shares fixtures with (`src/pewpew/rig/electrical.py:840-856`). `rig.issues` is capped as `RigError` is, by a shared `capped` (`src/pewpew/rig/models.py:760`, `src/pewpew/rig/compile.py:105`). The review's 200-feed case gives 101 issues. The basis now records each (fact, use) once (`electrical.py:482-492`), so that case compiles in 106 ms, not 263 ms. Test: E `test_overlapping_feeds_give_one_issue_a_feed_and_issues_are_capped`.
4. **Fixed.** A feed stops at its PSU's `psu_load_fraction × i_max_a` (`wiring.py:334`). A fixture over a whole PSU's share goes on the first PSU of its voltage, and no PSU is added (`wiring.py:359-360`). Test: W `test_a_feed_never_outgrows_its_psu`.
5. **Fixed.** The per-output cap also takes the least board limit, `min(max_px_total, max_px_advised)`, of the declared boards (`wiring.py:117-120`, `:175-181`). An empty board takes a chain that is over its limit, so no declared board is left empty for it (`wiring.py:199`). Test: W `test_a_chain_fits_the_board_pixel_limit`.
6. **Fixed.** An added board copies the first declared controller whose firmware drives the chain's pixel format (`wiring.py:241-245`). The report's notes and position basis name that controller (`electrical.py:611-624`). Test: W `test_an_added_board_has_a_profile_that_drives_the_chain`.
7. **Fixed.** Feeds go only to PSUs whose `v_out` is the feed's `v_nominal`, or to any PSU if none matches. An added PSU copies the first declared PSU of that voltage (`wiring.py:351-357`). Test: W `test_feeds_go_to_a_psu_of_their_voltage`.
8. **Fixed for `passthrough_ohm`; skipped for `measured_w`.** Each link's resistance adds the pass-through of the fixture before it, in auto-wiring and in the report (`electrical.py:240-248`). A pass-through that is given but not measured goes in the basis. `measured_w` is skipped because design §9 item 5 fills it from several bench readings (full white and each channel alone, `docs/studio/domain-model.md:378`), and which reading replaces `max_w` is a decision for the maintainer. Test: E `test_a_measured_pass_through_adds_to_the_drop`.
9. **Fixed.** `Ingest.auto_white` is one of WLED's five modes, and None means `manual` (`models.py:368-378`). Effect power uses the mode of each fixture's controller firmware, as R + G + B + a·min + b·max (`electrical.py:136-146`, `:287-347`). An unwired RGBW fixture takes Accurate, and the basis lists that as assumed (`electrical.py:551-558`). Tests: E `test_auto_white_terms_follow_wled_for_every_mode` (a port of WLED's `autoWhiteCalc`), `test_effect_power_follows_the_firmware_auto_white` and `test_unwired_rgbw_fixtures_take_accurate_white_as_an_assumption`.
10. **Fixed as a note; the packing rule is left to the maintainer.** When a chain takes feeds from more than one PSU, the report notes that V+ must stay open at every feed boundary and that every supply's negative is joined (`electrical.py:1000-1006`). Packing whole chains per RES-032 would need 6 PSUs for the golden rings, not 5 (review arithmetic). Test: W `test_a_chain_fed_from_two_psus_gets_a_note`.
11. **Fixed.** The report keeps added controllers and added PSUs apart (`electrical.py:543`, `:611-624`). Test: W `test_a_declared_id_never_reads_as_added`.
12. **Fixed.** `wiring.link_conductors` lists every cable of a feed with links (`electrical.py:565-567`). Test: E `test_the_link_conductor_basis_names_every_feed_cable`.
13. **Fixed.** The catalog refuses a PSU `v_out` or `i_max_a`, a connector `rated_a`, a cable conductor area, or a chipset `bit_s` or `bits_per_channel` that is 0 or below, and a negative `passthrough_ohm` (`src/pewpew/rig/catalog.py:403-416`, `:512-531`). Test: E `test_a_zero_divisor_in_the_catalog_is_refused`.
14. **Fixed.** One `has_conductors` (`electrical.py:89`) serves `lowest_loss_cable`, the auto feed cable and explicit feeds (`wiring.py:277`, `:305`; `compile.py:335`). `EPS` is defined once, in `electrical.py:68`. Test: W `test_a_cable_without_power_conductors_is_never_a_feed_cable`.

## Golden rings

They still compile to 2 boards, 6 chains, 24 feeds, 5 PSUs and 1,228.8 W. Two parts of the report
change: `wiring.link_conductors` is now the list `["wire-16awg-pair"]` (finding 12), and a new note names
`c1.rmt1`, `c1.rmt2` and `c1.rmt3`, which take feeds from two PSUs (finding 10).

## Other corrections

- `ws2-simplify.md` said that `contracts.md` lists `build_report`. It does not (`grep -n build_report
  docs/studio/contracts.md` finds nothing), so that line is corrected.
- "The rule as built" in `docs/studio/reports/ws2-wiring.md` describes the rule before these fixes.
  The module docstring of `wiring.py` describes the current rule.

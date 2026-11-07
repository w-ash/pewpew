# ws2: wiring and electrical

Workstream 2 replaced the auto-wiring stub and built the power, wiring and controller report.
`compile_rig` now fills `rig.report`, `rig.feeds`, the final `slices` and `issues`, and
`rig.power`, which backs `CompiledRig.estimate_effect_power(frame_linear)`. After merging `studio`
(`6a51447`, `c09cf3e`), `uv run --all-extras --all-groups pytest` passes 383 tests (2 xfailed) in
about 3 s.

## What is where

| Where | Contents |
|---|---|
| `src/pewpew/rig/wiring.py` | `auto_wire` (`:53`), the six-step rule in its module docstring; `fixture_cap` (`:130`), `lowest_loss_cable` (`:240`) |
| `src/pewpew/rig/electrical.py` | the arithmetic (`max_px`, `frame_s`, `loop_ohm_per_m`, `feed_drop_v`, `fuse_window`, `pick_fuse`, `accurate_white`, `:70-127`); ports and cable runs (`:133-180`); `Site` and `FeedLoad` (`:182-238`); `EffectPower` and `effect_power_model` (`:243-293`); the report models (`:296-414`); `build_report` (`:462`) |
| `src/pewpew/rig/models.py` | `Power.model` and `DEFAULT_POWER_MODEL` (`:239-277`), `Controller.components` (`:402`), `AutoWiring.feed_cable` (`:655`), `WiringPlan.controllers` and `.psus` (`:769`), `CompiledRig.power` and `estimate_effect_power` (`:845`) |
| `src/pewpew/rig/compile.py` | runs on declared plus added controllers and PSUs; calls `build_report` after the finite-mapping check (`:91`) and `effect_power_model` (`:108`) |
| `tests/test_rig_wiring.py`, `tests/test_rig_electrical.py` | design §8 items 6 to 9, the validation tiers and effect power |

## The rule as built

1. **Runs.** Consecutive fixtures that share group, chipset and channels.
2. **Hop breaks.** A run breaks where `|out − in| × hop_slack + pigtails` is over `max_hop_m`.
3. **Even chains.** Each piece is cut into ⌈F/c⌉ chains, with
   `c = ⌊min(firmware cap, max_px(t_px, reset, fps))/px⌋`, capped by `fixtures_per_output` and at
   least 1. Sizes differ by at most one.
4. **Outputs, first fit.** An output takes a chain if the firmware has its LED type, any
   `same_led_type` group keeps one type, and the board stays within `min(max_px_total,
   max_px_advised)`. When no board fits, a board of the first declared profile, at its position, is
   added as `c<k>` (k from the declared count + 1, skipping used ids). Chain ids are
   `<controller>.<output>`.
5. **Feeds, greedy.** A feed grows while `I ≤ connector_load_fraction × rated_a` and its end drop is
   within `max_drop_fraction`. The cable is `feed_cable`, or the catalog cable with the lowest loop
   resistance per metre. Each feed's length is `|PSU − first fixture's in| × hop_slack`.
6. **PSUs, first fit.** A PSU takes a feed while its load is within `psu_load_fraction × i_max_a`.
   When none has room, a PSU of the first declared type, at its position, is added as `p<k>`.
   Each feed gets the smallest regular blade fuse in `[I/0.75, rated_a]`.

The explicit-wiring path is unchanged, and the same report and checks run on it, against
`AutoWiring`'s default limits and `Wiring.target_fps`.

**Report.** It has `target_fps`, `limits`, totals, controllers (with `derived`), outputs, hops
(`lead` and `link`), feeds, PSUs, a bill of materials, `basis` and `notes`. `basis` lists every
unmeasured value a result rests on, with its status, source and which results use it.

**New issues.**
- **Violations:** `feed_over_rating`, `fuse_outside_window`, `psu_overload`, `psu_voltage`,
  `feed_overlap`.
- **Warnings:** `fps_below_target`, `drop_over_limit`, `hop_over_limit`, `lead_over_limit`,
  `psu_over_derating`, `feed_unfused`, `unfed`, and `rests_on_assumed`, one per assumed fact.
- **Errors:** `no_conductors`, and `unresolved_ref` for `wiring.auto.feed_cable`.

## Decisions and deviations

1. **Full white on an RGBW bar is a quarter of `max_w`.** Accurate auto-white turns RGB white into
   W alone ([bus_manager.cpp L102-L125](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125)).
   The `linear` model weights every channel equally, as WLED's own estimator does
   ([L196-L206](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L196-L206),
   [L285-L289](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L285-L289)).
   So an RGB white frame draws `max_w/4` per bar, yellow draws `max_w/2`, and a tube at white
   draws its full 36 W.

   I read the brief's "full white equals max_w" as every channel full. That is how QuinLED's table
   names its maximum ("RGB White + W 100%") and what Clen's 25.6 W means (inference). The test
   checks it on the coefficients: each fixture's per-pixel channel watts × channels sums to
   `max_w`. A frame can reach that only on RGB fixtures.
2. **The f1 drop is 0.172 V, not 0.169 V.** The design gives no link resistance rule, and its
   0.0528 Ω could not be reproduced from any geometry (inference: it looks like 2 m of 16 AWG at
   13.2 mΩ/m). I model each link as the data hop path, `|out − in| × 1.2 + 0.6 m` of pigtails =
   2.135 m, on the feed cable's conductors, and flag that as assumed.
   `feed_drop_v([1.067, 1.067], 0.0527, [0.0528])` reproduces the design's 0.169 V, and the
   compiled f1 gives 0.0527 Ω × 2.133 A + 0.0562 Ω × 1.067 A = 0.172 V (0.72%).
3. **Hop lengths use the `in` and `out` connector anchors.** The straight hop on the ring of 8 is
   1.279 m; the design's 1.274 m is between `end_b` and `end_a`. Its "1.53 m with slack" also
   leaves out the pigtails that its own formula adds (`domain-model.md:221`, `:239`). I follow the
   formula.
4. **Hop breaks come before even sizing**, so a break never leaves a short tail. The design lists
   the two steps the other way round.
5. **The 10-bar chain is 38.9 fps** with the 80 µs reset (`domain-model.md:362`). RES-031 gives
   "about 39" with a 300 µs latch gap.
6. **No PSU or controller is guessed from the catalog.** Without a declared controller, everything
   stays `unwired`. Without a declared PSU, nothing is fed, and an `unfed` warning says to declare
   one. A missing `position_m` means the world origin, flagged as assumed once for the declared
   placement that added ones copy.
7. **golden-rings.json gained `"psus": [{"id": "p1", "type": "meanwell-lrs-350-24"}]`** so its
   report has feeds. Its pixel order is unchanged, because the chains follow authoring order.
8. **Level shifters are data.** `Controller.components` names parts per board. The S3 file gained
   one 74AHCT125 per board (RES-031, PRT-006, RES-030). The Dig-Octa has none, because its outputs
   are already shifted.
9. **Fuse ratings** are the regular blade series 0.5 to 40 A
   ([Automotive fuse, rev. 1356410187](https://en.wikipedia.org/w/index.php?title=Automotive_fuse&oldid=1356410187#Blade_type)).
   Littelfuse's pages returned 403, so the ATO datasheet itself was not read.
10. **Changes to ws1's files:** `models.py` (fields above), `compile.py`, `catalog.py`
    (`power.model` in `to_json`), the S3 data file, the example, the schemas, and four
    stub-era assertions in `tests/test_rig_compile.py` and `tests/test_runner.py`.

## Golden rings (`src/pewpew/rig/examples/golden-rings.json`)

| | Default cap (9) | `fixtures_per_output: 4` |
|---|---|---|
| Boards | 2 (c1, plus c2 added) | 3 (c1, plus c2 and c3 added) |
| Outputs | 6 chains of 8 bars, 512 px, 20.56 ms, 48.6 fps | 12 chains of 4 bars, 256 px, 10.32 ms, 96.9 fps |
| Data hops | 42 links, 1.84-1.88 m; leads 1.19-1.63 m | 36 links; 12 leads |

These rows are the same at both settings:
- **Feeds:** 24 feeds of 2 bars, each 2.133 A with a 3 A fuse, on 0.89-1.33 m of 16 AWG. The
  worst drop is 0.128 V (0.53%).
- **PSUs:** 5 LRS-350-24 (p1 plus p2 to p5 added). p1 to p4 carry 10.67 A (73%) and p5 8.53 A.
- **Worst case:** 3072 px, 1228.8 W, 51.2 A.
- **Effect power:** 307.2 W at white and 614.4 W at yellow.
- **Issues:** seven `rests_on_assumed` warnings, on the connector rating, the pigtail, the power
  model, the pass-through, the link conductors, and the c1 and p1 positions. No violations.

Compiling takes about 5 ms. `estimate_effect_power` takes about 95 µs at 3072 px and 345 µs at the
200-bar cap (12,800 px).

## Merge of `studio`

`git merge studio` (`cb1e3c0`) completed with no textual conflicts. I checked these after it:
- **`Wiring.target_fps`.** `build_report` reads it for explicit wiring. A test fires
  `fps_below_target` on a 10-bar chain at `target_fps: 40`.
- **Schemas.** Regenerated after the merge, with no diff.
- **The hardening's `not_finite` mapping check.** It now runs before `build_report`, so a
  non-finite placement raises `RigError` instead of reaching the report's finite-only models.
  Validated positions are capped at 10 km (`MAX_POSITION_M`), so this matters only for
  constructed models.
- **The Rainbow golden.** It still matches, because the pixel order did not change.

## Open issues

- **Measurements decide the numbers.** Everything in design §9.5 is still open: watts off and at
  full white, per-channel watts, and the pass-through resistance (Q-004, Q-010). If a bar measures
  flat, set `"power": {"model": {"v": "flat", ...}}` on its fixture type.
  - QuinLED's single-addressable 24 V SK6812 strip read 52.70 W in every row, noted "Always uses
    max power".
  - Its 24 V SK6812 RGBW strip with one IC per 6 LEDs drew about 23 W above idle for W alone and
    about 12 W for each of R, G and B (5.46 W off, 28.50 W W alone, 17.44 W red alone).
    Equal weights may therefore understate white (inference).
- **`measured_w` and `passthrough_ohm` are not used yet.** The drop leaves out the pass-through
  and lists it in `basis`.
- **Cable ampacity** is not in the catalog, so a feed cable is not checked against its current.
- **Auto-wiring packs PSUs without matching voltage.** A mismatch shows only as a `psu_voltage`
  violation.
- **Contract additions** for ws3 and ws4:
  - `rig.report` is `electrical.RigReport`;
  - `rig.power` exists;
  - `AutoWiring.feed_cable`, `Power.model` and `Controller.components` are new;
  - catalog JSON gains `power.model`.

## Sources

- Design and contracts: `docs/studio/domain-model.md:38-41`, `:217-243`, `:302-321`, `:362-365`;
  `docs/studio/contracts.md:59-67`; A3 report, `docs/studio/planning/2026-10-22-a3-power-wiring-controllers.md`.
- Fixture record: the maintainer's fixture notes (not public), RES-030 to RES-033 and RES-018,
  plus Q-004 and Q-010. The RES-033 arithmetic (2 bars at 2.133 A fit and 3 bars at 3.2 A fail at
  3 A; 2 tubes at exactly 3.0 A fit) and the RES-032 totals (25.6 W and 1.07 A per bar) are tested.
- WLED v16.0.1, read from the tag:
  [bus_manager.cpp L102-L125](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125),
  [L196-L206](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L196-L206),
  [L285-L289](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L285-L289), and
  [const.h L266-L271](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L266-L271) (the auto-white modes).
- QuinLED 24 V power table, read as an image:
  https://quinled.info/wp-content/uploads/2020/03/LED-power-table_24v_v1.07b.png
- Fuse ratings: https://en.wikipedia.org/w/index.php?title=Automotive_fuse&oldid=1356410187#Blade_type
- Copper resistivity: https://en.wikipedia.org/wiki/International_Annealed_Copper_Standard
- Through the design, and not opened by ws2:
  - hop: https://auschristmaslighting.com/threads/maximum-distance-between-ws2811-pixel-nodes.7607
  - drop: https://quinled.info/the-ultimate-led-strip-power-injection-guide/
  - PSU loading: https://flexfireleds.com/blog/LED-power-supply-derating
  - fuse loading: https://info.littelfuse.com/hubfs/Fuseology%20Design%20Guide.pdf
  - Class 2: https://www.superbrightleds.com/blog/is-there-a-difference-between-class-2-and-class-ii-power-supplies.html
    and https://www.ecmweb.com/national-electrical-code/code-basics/article/20888526/classifying-and-using-c
  - TI SN74AHCT125 (through RES-030): https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf

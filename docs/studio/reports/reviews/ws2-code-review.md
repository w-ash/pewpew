# Code review of the ws2 wiring and electrical model (high effort)

- **Reviewer:** an independent agent (Opus), not the author. It ran the `code-review` skill at
  high effort and read the author's report only after its own review.
- **Target:** `git diff studio...HEAD` at `1ceccf9`, on 2026-10-22.
- **Verdict:** the arithmetic matches the design and the fixture record. 14 findings, all
  CONFIRMED. The worst: auto-wiring sizes feeds for the wrong PSU, and options that pass
  validation make `compile_rig` raise a raw exception.
- **Fixes:** the fix pass records what it did with each finding in `ws2-fixes.md`.

The studio code cited below is on the `studio` branch at `ed6032d`, which is outside the review
target. The probes were run from the clone with `uv run python`.

## Findings, most severe first

**1. Auto-wiring sizes every feed for the first PSU's position.** CONFIRMED
- **Where:** `src/pewpew/rig/wiring.py:281-308`.
- **Defect:** `fits` measures the feed cable from `arrangement.psus[0].position_m` (`:287`).
  First-fit can then put the feed on a different declared PSU at a different position (`:301`).
  The drop is not checked again for that PSU (`:308`).
- **Scenario:** 12 bars 1 m apart, `p1` at `[0, 0, 0.5]`, `p2` at `[0, 0, -40]`,
  `feed_cable: wire-18awg-pair`. `p1` takes f1 to f5 (10.67 A). f6 (2 bars) goes to `p2` on
  49.5 m of cable, with a 4.52 V drop (18.8%). The compiled rig then warns `drop_over_limit` on a
  feed that auto-wiring sized itself. With `p2` as the only PSU, the same rule makes 1-bar feeds
  and gives no warning.
- **Fix:** choose the PSU first, then grow the feed against that PSU's position.

**2. Options that pass validation overflow, and `compile_rig` raises a raw exception.** CONFIRMED
- **Where:** `src/pewpew/rig/models.py:628` (`Feed.length_m`) and `:648-654` (`AutoWiring`).
  The exceptions come from `electrical.py:72`, `:607`, `:717`, `:863-869` and `wiring.py:311`.
- **Defect:** `target_fps`, `hop_slack`, `connector_load_fraction` and `Feed.length_m` have no
  bound that keeps the arithmetic finite. The report models refuse inf (`allow_inf_nan=False`,
  `electrical.py:297`), so pydantic raises.
- **Scenario:** each of these arrangements passes `load_arrangement`:
  - `target_fps: 5e-324` raises `OverflowError` from `math.floor(inf)` (`electrical.py:72`).
  - `hop_slack: 1e308` with bars 3 m apart, or `6e307` with bars 1 m apart, gives an infinite
    feed length, and pydantic raises `ValidationError` for `Feed` (`wiring.py:311`).
  - `connector_load_fraction: 5e-324` gives `fuse_window_a[0] = inf`, and pydantic raises
    `ValidationError` for `FeedReport`.
  - Two explicit feeds with `length_m: 1e308` give an infinite BOM cable length
    (`ValidationError` for `BomLine`). One 40-bar feed of 1.7e308 m gives `drop_v = inf`.
  - In a fuzz of 1,500 random valid arrangements, 167 raised one of these, and none of them
    raised `RigError`.
  - The studio catches `ValueError` and `OverflowError` (`studio:src/pewpew/studio/app.py:253`),
    so it returns a 422. The message is the raw pydantic text, for example "1 validation error for
    FeedReport ..." (`app.py:121-126`). The contract says errors raise `RigError` with issues
    (`docs/studio/contracts.md:54`).
- **Fix:** bound the options in `AutoWiring` and `Feed.length_m`. For example, set `target_fps`
  ≥ 0.1, `hop_slack` ≤ 10, each fraction ≥ 0.01 and `length_m` ≤ `MAX_SPAN_M`. Also, if
  `build_report` gets a non-finite result, raise `RigError` with a `not_finite` issue.

**3. One arrangement can return 40,000 issues.** CONFIRMED
- **Where:** `src/pewpew/rig/electrical.py:744-750` (`_coverage`).
- **Defect:** the code adds one `feed_overlap` violation per fixture per extra feed. Only
  `RigError` caps issues (`models.py:730-734`); `rig.issues` has no cap.
- **Scenario:** one chain of 200 bars with 200 explicit feeds, each of which covers the whole
  chain (45 KB of JSON). The result has 40,408 issues (39,800 of them `feed_overlap`), a 5.9 MB
  `to_json()`, and takes 0.29 s to compile. The studio also puts every issue in the websocket
  bind result (`studio:src/pewpew/studio/app.py:269`). At 60 compiles per minute per address
  (`studio:src/pewpew/studio/limits.py:23`), one address can pull about 350 MB a minute
  (arithmetic).
- **Fix:** give one `feed_overlap` per pair of feeds that lists the shared fixtures, and cap
  `rig.issues` as `RigError` does.

**4. A feed can be too big for any PSU, and auto-wiring then adds PSUs that overload.** CONFIRMED
- **Where:** `src/pewpew/rig/wiring.py:276-279`, `:301-306`.
- **Defect:** `fits` limits a feed only by the connector rating and the drop. A feed over
  `psu_load_fraction × i_max_a` fits no PSU, so auto-wiring adds a new PSU for it, and that PSU
  cannot carry it either. The declared PSU stays empty.
- **Scenario:** these runs use temporary catalog copies, except the last one.
  - Bars with no connector at 80 W: one 16.67 A feed of 5 bars goes to an added `p2` (14.6 A),
    which gives `psu_overload`. The declared `p1` carries 0 A.
  - Bars at 400 W (16.7 A each): 3 feeds go to 3 added PSUs, each with `psu_overload`, and `p1`
    stays empty.
  - The bundled catalog with `psu_load_fraction: 0.01`: 11 feeds go to 11 added PSUs, each with
    `psu_over_derating`, and `p1` carries none.
- **Fix:** also stop a feed at `psu_load_fraction × i_max_a` of the PSU type. When one fixture
  alone is over that limit, put it on a declared PSU and report the violation; do not add PSUs.

**5. A chain over a board's pixel limit leaves the declared board empty.** CONFIRMED
- **Where:** `src/pewpew/rig/wiring.py:130-138`, `:165-168`, `:209-219`.
- **Defect:** `fixture_cap` caps a chain only by the firmware's per-output cap. It does not use
  the board limit `min(max_px_total, max_px_advised)` (`:180-186`). `free_output` then refuses
  the chain on every board, and the chain goes to a new board that is forced to take it.
- **Scenario:** one declared Dig-Octa (it advises 2,000 px), 64 bars, `target_fps: 1`. This
  gives 2 chains of 2,048 px. The declared `c1` gets no chain. Added `c2` and `c3` get one chain
  each, with two `controller_over_advised` warnings.
- **Fix:** cap the pixels of a chain at `min(per-output cap, board limit)`, or let an empty board
  take an oversized chain before you add a board.

**6. An added controller always has the first declared profile.** CONFIRMED
- **Where:** `src/pewpew/rig/wiring.py:209-216`.
- **Scenario:** declared controllers `a` (a test RGB-only board with one output) and `b` (the
  S3), and 45 bars in 5 chains. `b` takes 4 chains. For the fifth chain, auto-wiring adds a board
  with `a`'s profile, which has no RGBW LED type. The 9 bars of that chain are `unwired`, with the
  message "test-rgb-board has no output for their pixel format", but another S3 board could carry
  them.
- **Fix:** add a board of the first declared profile whose firmware has the LED type of the
  chain.

**7. PSU first-fit does not check voltage.** CONFIRMED. The author's report lists it as open
(`docs/studio/reports/ws2-wiring.md:141-142`).
- **Where:** `src/pewpew/rig/wiring.py:301`, `:305`.
- **Scenario:** declared PSUs `p1` (a test 5 V PSU) and `p2` (LRS-350-24), and 24 V bars. Both
  feeds go to `p1`, and the compiled rig has a `psu_voltage` violation, but `p2` could carry them.
- **Fix:** use only PSUs whose `v_out` matches the `v_nominal` of the feed, and add PSUs of a
  declared type that matches.

**8. Measured values do not reach the arithmetic.** CONFIRMED. The author's report lists it as
open (`ws2-wiring.md:138-139`).
- **Where:** `src/pewpew/rig/electrical.py:220-236` (`Site.feed`), `:687-691`;
  `src/pewpew/rig/catalog.py:184-185`.
- **Defect:** the code reads `passthrough_ohm` only to record that it is missing. It never reads
  `measured_w`; current and worst case use only `max_w`. Design §9 item 5 says the bench
  measurements fill these two fields (`docs/studio/domain-model.md:378`).
- **Scenario:** a bar with a measured pass-through of 0.5 Ω and a measured 12 W. The drop of f1
  stays 0.0983 V, and its current stays 2.133 A. The pass-through would add about 0.53 V for the
  1.067 A of bar 1 (arithmetic). The basis still lists `max_w` as `stated`.
- **Fix:** in `feed_drop_v`, add `I_down × passthrough_ohm` for each upstream fixture. Decide how
  `measured_w` replaces `max_w`; the design does not say (not found).

**9. Effect power always applies Accurate auto-white.** CONFIRMED
- **Where:** `src/pewpew/rig/electrical.py:287`. The code never reads the firmware's
  `ingest.auto_white` (`models.py:357`).
- **Scenario:** with `auto_white: null` in a test copy of the firmware, RGB white on 2 bars still
  gives 12.8 W. In WLED's manual-only mode, W stays 0 and R, G and B stay full
  (https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125). Then the 2 bars
  would draw 3 × 6.4 × 2 = 38.4 W (inference from that code). An unwired RGBW bar has no
  firmware, but it also gets Accurate (6.4 W). The basis does not list the auto-white assumption.
- **Fix:** read `auto_white` from the firmware of each chain, and map each of WLED's modes. For
  unwired fixtures, add a basis entry.

**10. The feeds of one chain can come from two PSUs, against RES-032.** CONFIRMED (behavior). The
design does not cover it.
- **Where:** `src/pewpew/rig/wiring.py:298-307`.
- **Defect:** first-fit packs feeds, not chains. RES-032 says "Feed each chain from one supply"
  and "never join the V+ of separate supplies" (the maintainer's fixture notes,
  RES-032). The split-V+ feed (`domain-model.md:50`, after RES-033) keeps two supplies apart only
  if V+ is open at every feed boundary. The report does not tell the builder this.
- **Scenario:** in the golden rings, chains `c1.rmt1`, `c1.rmt2` and `c1.rmt3` each take feeds
  from two PSUs (p1 and p2, p2 and p3, p3 and p4).
- **Fix:** the maintainer decides. Either pack whole chains, which would need 6 PSUs for the golden rings
  because two 8.53 A chains are over 11.68 A (arithmetic). Or keep feed packing, and add a note
  that V+ must be open at each feed boundary between PSUs.

**11. A declared id that equals an added id of the other kind is marked derived.** CONFIRMED
- **Where:** `src/pewpew/rig/electrical.py:482`, used at `:501`, `:527` and `:604`.
- **Defect:** the `derived` set holds both controller and PSU ids.
- **Scenario:** the golden rings with controller `c1` renamed to `p2`. Auto-wiring adds PSU `p2`,
  and the report gives controller `p2` as `derived: true`.
- **Fix:** keep one set for controllers and one for PSUs.

**12. The link-conductor basis gives only the cable of the first feed.** CONFIRMED
- **Where:** `src/pewpew/rig/electrical.py:683`. `_Bases.add` keeps the first value (`:427`).
- **Scenario:** explicit feeds on 16 AWG and 18 AWG. `wiring.link_conductors` in the basis is
  `wire-16awg-pair`, and the warning says so for both feeds.
- **Fix:** use one fact per cable (`wiring.link_conductors.<cable>`).

**13. Zero values in the catalog divide by zero.** CONFIRMED. An arrangement cannot cause it.
- **Where:** `src/pewpew/rig/electrical.py:82`, `:792`. The catalog checks only `span_m` and
  `v_nominal` for > 0 (`catalog.py:396-402`).
- **Scenario:** a catalog copy with `i_max_a: 0`, or with both conductors at 0 mm², makes
  `compile_rig` raise `ZeroDivisionError`. The studio does not catch it (`app.py:253`), so a
  request would get a 500.
- **Fix:** in the catalog checks, require `i_max_a`, `v_out`, `rated_a`, the conductor areas and
  `bit_s` to be above 0.

**14. One rule has three copies.** CONFIRMED (grep)
- **Where:** the "has a V+ or GND conductor" check is at `wiring.py:245`, `:270` and
  `compile.py:334`. `_EPS` is defined at `wiring.py:47` and at `electrical.py:64`.
- **Fix:** use one helper in `electrical` and one `_EPS`.

## Checked and sound

- **Auto-wiring rule.** Runs, the cap, the even cut, output first-fit (with `same_led_type` and
  board totals), greedy feeds and PSU first-fit agree with `domain-model.md:217-226`. The
  exceptions are findings 1, 4 and 5, and the documented change of order between hop breaks and
  the even cut (`wiring.py:22-23`). Auto-wiring of the design's example (`domain-model.md:169`,
  `fixtures_per_output: 4`) gives the same chains, the same feeds (2+2, 2+2, 1) and the same pixel
  order. The tube gets a 2 A fuse, the smallest in its [2.0, 4] A window, where the design used
  3 A. The golden rings give 2 boards, 6 chains of 8, 24 feeds, 5 PSUs and 1228.8 W; at 4 per
  output they give 12 chains on 3 boards.
- **Determinism.** Five processes, with `PYTHONHASHSEED` 0, 1, 2, 12345 and random, gave the same
  SHA-256 of `to_json()`, the same mapping bytes and the same effect-power float (compared as
  hex). The three rigs were the golden rings, the golden rings at 4 per output, and a mixed rig of
  50 fixtures with two profiles and two PSUs. Sets are sorted before output, ids come from
  counters, and sums run in data order (`math.fsum` for the totals).
- **Arithmetic against the design.** `max_px` gives 623. A 10-bar chain runs at 38.94 fps, and a
  6-tube chain takes 6.504 ms. 2 bars (2.133 A) fit a feed, 3 bars (3.2 A) do not, and 2 tubes fit
  at exactly 3.0 A with a [4.0, 4.0] A window. The f1 window is 2.84-4.0 A with a 3 A fuse. The
  PSU carries 10.03 A (69%), the total is 240.8 W, and there are 548 px. The drop at f1 is
  0.172 V, not 0.169 V, because each link uses the hop path with its pigtails (2.135 m). With the
  design's 0.0528 Ω, `feed_drop_v` gives 0.169 V. 0.0528 Ω is about 2.0 m of the 16 AWG loop
  (arithmetic). The test records this (`tests/test_rig_electrical.py:130-136`).
- **Arithmetic against RES-031 to RES-033** (the maintainer's fixture notes).
  For 60 bars and 17 tubes the report gives 2148.0 W and 89.50 A; RES-032 says about 2150 W and
  90 A. A 10-bar chain draws 10.67 A and a 6-tube chain 9 A, as in RES-032. At `target_fps: 38`
  the bars make 6 chains of 10 at 38.9 fps; RES-031 says 6 chains of 10 at about 39 fps. RES-031
  uses a 300 µs latch, which gives 38.61 fps. At 40 fps the cap is 9 bars with either latch
  (⌊24.7 ms / 40 µs⌋ = 617 px; arithmetic). A 6-tube chain runs at 153.8 fps with the 24 µs
  reset, against 147 fps in RES-031 with 300 µs. At 40 fps the 17 tubes go on one output (the cap
  is 23 tubes), where RES-031 uses 3 tube chains. That is a layout choice, not a limit
  (inference). The RES-033 feed sizes hold.
- **Accurate auto-white.** `accurate_white` is WLED's `RGBW_MODE_AUTO_ACCURATE`: W is the lowest
  of R, G and B, and each of R, G and B gives that much up
  (https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125; mode 2 at
  https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L266-L271). WLED sums R + G + B + W
  after auto-white and divides by 4 × 255 for RGBW
  (https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L196-L206,
  https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L285-L289). The code does the
  same with `channel_w` × the channel sum. WLED also adds 1 mA of standby per LED (L206). The code
  has no idle term, so an all-off frame is 0 W; the basis lists the `linear` model as assumed. The
  only defect is finding 9.
- **Fuse windows, drop and packing at the edges.** The limits are inclusive. A [4.0, 4.0] A window
  gives a 4 A fuse. Four 2.92 A feeds fill one PSU to exactly 11.68 A (80%). `max_px` is exact at
  a frame boundary (623 and 100). A PSU at the `in` port gives the 1 mm minimum feed and a 28 µV
  drop. A single fixture over every limit gets a 1-fixture feed with `feed_over_rating` and
  `feed_unfused` (its window is empty); the PSU side is finding 4.
- **Derived controllers and PSUs.** Ids are `c<k>` and `p<k>`, with k from the declared count +
  1, and they skip declared ids (declared `c1` and `c3` give `c4`). An added one copies the
  position of the first declared one, and a missing position is flagged as assumed once. With no
  controller, nothing is wired and one warning says why. With no PSU, nothing is fed and an
  `unfed` warning says why. The collision across kinds is finding 11.
- **Bounded work.** Every auto case at the 200-fixture cap compiled in 12-21 ms: 200 bars; 200
  tubes at 1e6 fps (200 chains, 50 boards); `psu_load_fraction: 1e-300` (169 PSUs);
  `max_hop_m: 1e-9`; bars 50 m apart; 200 controllers and 200 PSUs; 200 one-member groups. A feed
  recomputes `Site.feed` at each step (`wiring.py:287`), which is O(L²) per chain. The connector
  limit keeps feeds at 2 fixtures in the bundled catalog, so this cost does not show. The only
  amplification is finding 3.
- **NaN and inf.** Only the paths in finding 2 put a non-finite number into the report. The frame
  path changes NaN and inf to finite values (`electrical.py:269`), so effect power stays finite.
  All other compiled cases serialize with `json.dumps(..., allow_nan=False)`.
- **Speed of effect power.** It takes 95 µs a call at 3,072 px and 347 µs at 12,800 px. Each call
  makes a float64 copy of the float32 frame, a `nan_to_num` copy and an (N, 4) concatenate, and
  computes both branches of `np.where`. A version without that work took 49 µs and 187 µs and gave
  the same result. At 2 Hz and 20 sessions (`studio:src/pewpew/studio/limits.py:21`), the present
  cost is at most 14 ms a second (arithmetic), so this is not a finding.
- **The author's report.** Its numbers reproduce: 383 passed and 2 xfailed, compile in about 5 ms,
  95 µs and 345 µs for effect power, a worst drop of 0.128 V (0.53%), 42 links of 1.84-1.88 m,
  leads of 1.19-1.63 m, 307.2 W at white and 614.4 W at yellow, and seven `rests_on_assumed`
  warnings. It lists findings 7 and 8 as open issues.
- **Not found:** the "flat chord more than 1 mm from `housing_w`" warning
  (`domain-model.md:320`) is in no `src/pewpew/rig/*.py` file. It is a geometry check, outside the
  ws2 files (inference).

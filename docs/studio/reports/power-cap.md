# Power cap and brightness ceiling

A rig can now run under a software power cap, and the report buys supplies for what the rig
actually runs. The engine caps every frame, the arrangement stores the cap, the studio preview
shows the capped light, and the report sizes PSUs for the capped worst case.

- On the four BTF bricks the maintainer picked (12 chains of 4 bars), the ceiling is 62.5% brightness, which
  is L* 83.2. The conservative every-channel ceiling is 31.25%, which is L* 62.7.
- The golden rings' default auto-wiring now takes 3 Mean Well PSUs uncapped. At 18.4% brightness it
  takes 1.

## Design

**Engine: `src/pewpew/power.py`.** This is the power limit of architecture §2 stage 3, pulled
forward from Phase 2 and recorded in the ADR-001 amendment of 2026-10-23.

- `PowerCap(max_watts=None, max_brightness=1.0)` is the cap. `scale(variable_w, flat_w)` is the
  scale that keeps the worst frame under it, and `watts(...)` is the capped worst case.
  `max_watts` is over 0 and at most 1e6 W.
- `EffectPower` is the per-chip current model. It moved here from `rig/electrical.py`, so the engine
  owns its shape and the rig fills it from the catalog. A pixel draws `channel_w` × its channel sum
  after the firmware derives W, as WLED estimates it
  ([bus_manager.cpp L196-L206](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L196-L206)).
  `supply_of` gives each pixel's supply group. `flat_w` and `worst_w` give each group's flat draw
  and the most an RGB frame makes it draw.
- `PowerLimiter(cap, model)` cleans a linear frame as `to_display_u8` does (NaN to 0, clip to
  [0, 1]). It scales the frame by `max_brightness`, then holds the estimate under `max_watts`, by
  FastLED's estimate-and-scale [S413]. It returns `Limited(frame, scale, watts, uncapped_watts)`.
  - Cost: 68–70 µs a frame on the 3,072-pixel golden rings, in five runs on the dev laptop.
  - A cap that caps nothing passes the frame through unchanged.
  - The limiter never brightens a frame.
- `limit_stage(limiter, targets)` is a `PacedLoop` `on_frame` callable. It limits each frame, then
  hands it, read-only, to the sinks. It drops a frame that the limiter refuses and never sends it
  uncapped.

**Per-supply shares (a change from the brief; for the maintainer to confirm).** The brief's rule
is one scale, `min(1, max_watts / estimate)`. With more than one PSU, that rule lets a frame that
lights only one supply's fixtures put the whole cap on that supply.

- At 500 W the golden rings take 2 PSUs, and the report sizes p1 for 270.8 W.
- A frame that lights only p1's 26 bars at red and green full asks for 332.8 W. That is under the
  cap, so one global scale passes it, and p1 carries 95% of its 350.4 W rating. That is over the 80%
  the report promises.
- So the limiter splits `max_watts` across the supply groups in proportion to their worst-case
  draw, and it keeps each group within its share. The shares sum to the cap.
- An evenly lit frame gets the brief's scale exactly, and so does any frame on a one-supply rig.
- WLED's ABL also limits each bus against its own current
  ([bus_manager.cpp L1447-L1524](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L1447-L1524)).
- The cost: a frame lit on one supply gets that supply's share (270.8 W in the example), not the
  whole 500 W.

**The worst case follows the firmware's auto-white mode** (the coordinator's addition).

- pewpew sends RGB, and the board's WLED derives W from it in `autoWhiteCalc`
  ([bus_manager.cpp L102-L125](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125)).
- The estimate is linear wherever the order of R, G and B is fixed, so its largest value is at a
  corner of the RGB cube.
- `rgb_reach` gives that largest channel sum: 2 of 4 channels under Accurate (yellow has W = 0),
  3 under None, and 4 under Brighter, Dual or Max.
- A fixture's worst case is `max_w × reach / channels`: 12.8 W for a 25.6 W bar under Accurate.
- This rests on two assumptions, and the report flags both:
  - `max_w` is every channel full and splits evenly across them. One bar's per-channel watts are
    not measured (Q-004).
  - Every board runs Accurate.

**Format.** The arrangement takes an optional block, `"power": {"max_watts": float | null,
"max_brightness": float}` (`PowerLimit` in `src/pewpew/rig/models.py`).

- `max_watts` is over 0 and at most 1e6 W, `max_brightness` is 0 to 1, and the default caps nothing.
- The format stays version 1. A v1 file without the block loads and means what it meant before. A
  reader older than the block refuses a file that has it, as an unknown field.
- A bump to version 2 would make old readers refuse every new file, including files with no cap.

**Report** (`src/pewpew/rig/electrical.py`, `wiring.py`).

- **Totals.** `worst_w`/`worst_a` have every channel full. `rgb_worst_w`/`rgb_worst_a` are the most
  the RGB stream draws. `capped_w`/`capped_a` are that under the cap,
  `min(RGB worst case × max_brightness, max_watts)` with no flat-drawing fixture.
- **PSUs** are sized for the capped figure, with or without a cap, and auto-wiring packs them by it.
  Each PSU reports its capped load and its every-channel `worst_a`.
  - A PSU that only the cap or the auto-white keeps within its rating gets the warning
    `psu_full_white_overload`. A fallback preset that drives every channel would overload it.
- **Feeds without a cap** are checked as before, with every channel full.
- **Feeds under a cap** (option B, the coordinator's choice) work like this:
  - The cap is software. A fallback preset or a bug can exceed it, and WLED's own limiter warns
    that it is "NOT guaranteed to stay within the ablMilliampsMax margin"
    ([bus_manager.cpp L182-L187](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L182-L187)).
    So the hardware backstop is a fuse at each feed head, within the connector's rating.
  - The feed current, the connector check and the fuse window take the capped current.
  - A capped feed with no fuse is the violation `cap_without_fuse`.
  - A feed whose every-channel current is over its connector's rating gets the warning
    `relies_on_cap_and_fuse`. The warning names those amps and the fuse.
  - Voltage drop is always computed with every channel full.
- **PSU output connector.** A PSU's output connector (`psu.connector`) limits its feeds, as a
  fixture's input connector does.
- **Outputs** report `fps`: the wire's rate, at most the firmware's 15 ms minimum frame interval
  ([udp.cpp L477](https://github.com/wled/WLED/blob/v16.0.1/wled00/udp.cpp#L477)).
- **Boards** follow pixels and frame time, not watts.

**Catalog.**

- `psu/btf-24v-5a-120w`: 24 V and 5 A, both stated. The listing's spec field gives ETL listing, a
  plug-in AC cord and a 5.5 × 2.1 mm barrel output (https://www.amazon.com/dp/B09T6QX737, seen
  2026-10-23 and relayed by the coordinator; this workstream did not open the page).
- `connector/barrel-5.5x2.1`: rated 5 A, inferred from the brick's output, because the plug's own
  rating is not found. The bars' input connector stays at 4 A (assumed, as before).

**Studio.**

- `Session.bind(..., limiter=...)` replaces `power_fn`. Each frame passes the rig's limiter before
  `to_display_u8`.
- A frame that fails is dropped, and the limiter stays bound.
- An uncapped limiter runs only when a power reading is due, about 2 Hz.
- The `power` message is `{"type": "power", "watts", "uncapped_watts"}`. The web client reads an
  older one-field message as uncapped.
- The Report panel has a **Power cap** editor: Max watts, where empty means none, and Max
  brightness in percent.
  - Each edit commits to the arrangement under one undo key.
  - A cap that caps nothing removes the block, so an uncapped rig keeps its file and its share id.
  - The compile, the bind and the share link follow the arrangement.
- The summary shows "Every channel full", "PSUs sized for" with the RGB worst case beneath it, and
  the live watts with the uncapped figure beneath them.
- `openapi.json` does not change, because the routes take and return free-form JSON, so orval was
  not rerun.

**CLI.**

- `python -m pewpew run <pattern> --map rig.json` applies the arrangement's cap. `--max-watts W`
  and `--max-brightness B` each replace its value.
- `--max-brightness` works on any map.
- `--max-watts` needs an arrangement map, whose fixtures give the power model.

## The four-brick plan

Both examples take the golden rings' two rings on `btf-24v-5a-120w` bricks, with a 2 m 16 AWG feed
at each chain head. Each brick may carry 0.8 × 5 A = 4 A, or 96 W. Each bar's input connector is
4 A at the report's 75% loading, so 3 A.

| | `golden-rings-4-bricks.json` | `golden-rings-4-bricks-head-fed.json` |
|---|---|---|
| Layout | 12 chains of 4 bars on 3 boards × 4 outputs, `target_fps` 40 | 4 chains of 12 on 2 boards × 2 outputs, `target_fps` 30 |
| Feeds | 3 per brick, 3 A fuse each | 1 per brick, 4 A fuse each |
| Frame rate | 256 px, 10.32 ms: 96.9 fps on the wire, shown at WLED's 66.7 | 768 px, 30.80 ms: 32.5 fps |
| Ceiling, RGB worst case | **0.625**, set by the brick: 12 × 12.8 W × b ≤ 96 W | **0.46875**, set by the head: 12 × 0.533 A × b ≤ 3 A |
| Perceived, CIE L* | 83.2 | 74.1 |
| Each brick | 96.0 W, 4.0 A, 80% | 72.0 W, 3.0 A, 60% |
| Head current under the cap | 1.33 A, fuse window [1.78, 4] A | 3.00 A, fuse window [4.00, 4] A |
| Ceiling, every channel full | 0.3125 (brick: 12 × 25.6 W × b ≤ 96 W), L* 62.7 | 0.234 (head: 12.8 A × b ≤ 3 A), L* 55.5 |
| Violations | none | none |
| Warnings | `relies_on_cap_and_fuse` ×12: 4.27 A with every channel full, over the 4 A connector, behind a 3 A fuse. `psu_full_white_overload` ×4: 12.8 A on a 5 A brick. | the same pair ×4: 12.80 A behind a 4 A fuse, and 12.8 A on each brick. `drop_over_limit` ×4: 17.1–17.4% |
| Drop | 2.2–2.3%, with the bars' pass-through assumed 0 Ω | 17.1–17.4%, on the same assumption |

`test_four_brick_examples_run_at_their_largest_clean_brightness` computes each ceiling from the
uncapped compile. It takes the least of each feed's connector and fuse loading and each brick's
derating. It then checks that the file's `max_brightness` equals that ceiling, that the file has no
violations and no PSU over its derating, and that 0.01 more brings one.

**L\*.** L\* = 116 · Y^(1/3) − 16, with Y the relative luminance
([CIELAB](https://en.wikipedia.org/wiki/CIELAB_color_space#From_CIEXYZ_to_CIELAB)). This assumes
light output scales linearly with brightness. L\* is the perceptually correct lightness for
direct-view LEDs [S059][S061]. For reference, 18.4% brightness is L\* 50.0, the mid-grey of S061.

**The split layout wins on every count.** It is brighter (62.5% against 46.9%), and its drop is
2% against 17%. It shows 66.7 fps against 32.5. It takes one more board and three times the fuses.

## Golden rings at a few caps

This is the default auto-wiring of `golden-rings.json` on Mean Well LRS-350-24 supplies (24 V,
14.6 A, [datasheet](https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF)) at 80%, which is
280.3 W each. Every channel full is 48 × 25.6 W = 1,228.8 W. The RGB stream under Accurate draws
half of that, 614.4 W.

| Cap | PSUs sized for | PSUs | Feeds |
|---|---|---|---|
| none | 614.4 W | 3: 73.1%, 73.1%, 29.2% | 24 of 2 bars, 3 A fuses |
| 18.4% brightness | 113.0 W | 1: 32.3% | 6 of 8 bars, 2 A fuses |
| 50% brightness | 307.2 W | 2: 73.1%, 14.6% | 6 of 8 bars, 3 A fuses |
| 280 W | 280.0 W | 1: 79.9% | 6 of 8 bars, 3 A fuses |
| 500 W | 500.0 W | 2: 77.3%, 65.4% | 12 (6 of 6 bars, 6 of 2), 4 A and 2 A fuses |
| 1,000 W | 614.4 W | 3 | 12 (6 of 5 bars, 6 of 3) |

Every row keeps 2 boards. Under a cap the feeds grow, because the connector check takes the capped
current. Their length is then limited by the drop, which takes every channel full. With every
channel full, the uncapped rings took 5 PSUs. The brief's 226.1 W at 18.4% was 1,228.8 × 0.184; on
the RGB basis it is 614.4 × 0.184 = 113.0 W.

## Tests

- `tests/test_power.py` covers:
  - the cap arithmetic and its bounds;
  - the limiter at both edges: no cap passes the frame object through, a cap at the frame's own
    draw scales by 1, and zero brightness or a cap under the flat draw gives black;
  - that it never brightens a quantized byte, on seeded frames with out-of-range and non-finite
    values;
  - supply shares on a toy model and on the golden rings at 500 W;
  - determinism, and the rainbow golden unchanged through an uncapped and a loose limiter;
  - `limit_stage`, including a refused frame.
- `tests/test_rig_electrical.py` covers:
  - `rgb_reach` for every mode, and that yellow reaches the model's worst case;
  - the golden-rings table above;
  - the (B) feed rules, `cap_without_fuse`, `relies_on_cap_and_fuse` and `psu_full_white_overload`;
  - the PSU output connector;
  - the block's bounds and its round trip;
  - both four-brick examples.
- `tests/test_rig_wiring.py` runs the PSU-packing tests on a catalog set to Brighter auto-white, so
  their every-channel figures still hold. It adds a test that Accurate halves each PSU's load.
- `tests/test_studio.py` covers:
  - that the session streams the limited frame and both readings;
  - that a failed frame keeps the cap;
  - that an uncapped limiter runs only for readings;
  - that the real rig streams capped power.
- `tests/test_runner.py` covers the CLI flags.
- Web:
  - `powerOf` and `setPower`;
  - the editor's round trip into the document;
  - the protocol's new field and its reset on close.
  - `web/e2e/power.spec.ts` sets a cap, watches the report resize, saves a share link, opens it,
    and finds the cap kept.
- Gates: `uv run --all-extras --all-groups pytest` passes 575 with 2 xfailed. In `web/`,
  `pnpm check` passes, `pnpm test` passes 79, and `pnpm e2e` passes 4.

## Before buying supplies for a cap

- **Measure a bar.** The sizing holds only if the draw follows the frame and splits evenly across
  the channels. Both are assumed. The default power model's own note records that QuinLED measured
  a 24 V SK6812 strip at 52.70 W whatever it showed (`DEFAULT_POWER_MODEL` in
  `src/pewpew/rig/models.py`). Measure one bar on each channel alone, with every channel full, and
  at the chosen cap (Q-004).
- **Set Accurate on every board.** Under None an RGB frame reaches 3 of 4 channels, and under
  Brighter or Max all 4. Either would put the four-brick plan's bricks over their rating.
- **Back the cap up on the boards.** The cap lives in pewpew. When the stream stops, a WLED board
  falls back to its own state after a timeout [S645:wled00/udp.cpp#L410-L456] (req P-6), and that
  preset can drive every channel: 12.8 A against a 5 A brick. The fuses protect the connectors, but
  the bricks would be overloaded; how they respond is not found. Give each board a dim fallback preset and an ABL limit within its brick
  [S418]. Open decisions 34 and 35 list these.

## Records

- The ADR-001 amendment (2026-10-23) adds no new source. It cites [S413] (FastLED) and [S645]
  (WLED's ABL and auto-white), with [S418]. It rejects three alternatives:
  - WLED's ABL on the receiver;
  - one global scale;
  - feeds checked with every channel full under a cap, or a cap with no fuse.
- `research/synthesis/architecture.md` §2 stage 3 and §11 Phase 2 say that the limit landed early.
- `docs/studio/contracts.md` pins the block, the limiter API, the report fields and the `power`
  message, as of 2026-10-23.
- `CHANGELOG.md` has two Unreleased entries. The studio entry now says 3 PSUs.
- The project's list of open decisions, which is not in this repo, adds three items: the cap, the
  auto-white setting and the per-supply rule.

## Review

- The simplify pass (Sonnet) applied three small cleanups ([`reviews/power-cap-simplify.md`](reviews/power-cap-simplify.md)).
- The code review (Opus, high) found 2 medium and 6 low findings, all verified
  ([`reviews/power-cap-code-review.md`](reviews/power-cap-code-review.md)). The worst: one frame
  error switched the studio's cap off until the next bind.
- All are fixed except the per-supply rule, which is kept for the maintainer to confirm
  ([`reviews/power-cap-fixes.md`](reviews/power-cap-fixes.md)).

## Commits

On `studio-power-cap`, from `studio`:

- `d5b81d6` feat: power cap and brightness ceiling
- `e658c53` refactor: simplify the power cap
- `978045e` feat: size power for the auto-white worst case on four bricks
- this report and the open decisions, in the commit after `978045e`

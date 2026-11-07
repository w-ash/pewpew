# Power cap: code review

The review agent (Opus) ran the `code-review` skill at high effort on `studio..d5b81d6` ("feat:
power cap and brightness ceiling") and checked each claim itself. It found 2 medium and 6 low
findings, all verified. The most serious: in the studio, one exception in the frame handler
switches the cap off for the rest of the bind. At the commit, `uv run --all-extras --all-groups
pytest` passed (2 xfail), web `vitest run` passed 79 of 79, and `tsc --noEmit` was clean. The skill's
own pass ran no tests. The agent's probe scripts ran against an export of the commit in its
scratchpad; they are not committed.

## Verified findings

### 1. Medium: one frame error turns the studio's power cap off until the next bind

- **Where:** `src/pewpew/studio/session.py:195` and `:213-214`.
- **What:** the `except` in `_on_frame` sets `self._limiter = None`. Before this commit, the same
  line only stopped power messages (`_power_fn = None`). Now it removes the cap itself:
  - From the next frame on, the stream carries uncapped light and power messages stop.
  - The Report panel keeps showing the last capped reading.
  - Any exception in the `try` triggers this: the limiter, `to_display_u8`, `params.describe` or
    `sink.frame`.
- **Evidence:** a probe binds a limiter with `max_brightness=0` and makes `sink.frame` raise once:
  ```
  before fault: max byte 0 limiter PowerLimiter
  after fault: max byte of last frame 245 limiter None
  ```
- **Fix:** keep the limiter when a frame fails, and drop only that frame. If the limiter itself must
  be disabled, fail closed with a brightness-0 limiter, not uncapped. If power messages should still
  stop on an error, use a separate flag.

### 2. Medium (needs a decision): the watt cap is split per supply, not the spec's single global scale

- **Where:** `src/pewpew/power.py:176-198`. Each lit supply group is held to `s_full × full_w[g]`.
- **What:** the spec says `max_watts` scales by `min(1, max_watts / estimated_watts)`. The
  implementation caps each PSU at its share of the cap, so a frame that lights only part of the rig
  is dimmed even when its total draw is under `max_watts`. The ADR amendment records this on
  purpose (`ADR-001…md:98`, and the rejected alternative at `:132`), and its reason holds: with one
  global scale, PSUs sized for the cap could overload. But it contradicts the spec, and the ADR's own
  sentence at `:94` ("scales by `min(1, max_watts / estimate)`"), which also leaves out the
  flat-load subtraction.
- **Evidence:** the golden rings with `max_watts=500` take 2 PSUs (p1 270.8 W, p2 229.2 W). A frame
  that lights only p1's fixtures, red and green:
  ```
  one-PSU frame: uncapped 332.8 W, capped 270.8 W, scale 0.814
  spec global scale would be 1.0
  ```
  The studio would show 270.8 W and "332.8 W uncapped" while the cap is 500 W.
- **Fix:** the maintainer should confirm the per-supply rule. If it stays, change ADR line 94 to state the
  per-supply rule and the `(max_watts − flat)/variable` form. If the spec's literal rule wins, the
  report must size each PSU for its own worst case under a global scale, which loses the PSU savings
  (the golden rings at 500 W would need 5 PSUs, as the ADR notes).

### 3. Low: the estimate now runs on every frame, even for an uncapped rig

- **Where:** `src/pewpew/studio/app.py:272` always passes `rig.limiter()`, and `session.py:195`
  calls it on every frame. Before, the estimate ran only on power ticks (about 2 Hz).
- **Evidence:** at 16,384 px (`MAX_PIXELS`), a probe measured 326 µs per frame through the uncapped
  limiter, against 281 µs for one old `watts()` call. At 30 fps that is about 15× the estimate work
  per session, and 29 of 30 results are thrown away.
- **Fix:** when `not cap.caps`, pass the frame through and estimate only when
  `seq % _power_every == 0`.

### 4. Low (allowed by the spec, worth a warning): a near-zero cap puts the whole rig on one PSU with no issue raised

- **Where:** `src/pewpew/rig/wiring.py:321,339,371` packs PSUs by capped load, and
  `src/pewpew/rig/electrical.py:922-942` checks overload against the capped current only.
- **Evidence:** the golden rings with `max_brightness: 0` compile to 1 PSU, 24 feeds, 0.0 W capped,
  and `worst_a` 51.2 A on a 14.6 A supply. The only issue is `rests_on_assumed`. The report's own
  note says a fallback preset or a bug can exceed the cap.
- **Fix:** warn when a PSU's `worst_a` exceeds `i_max_a`, so the risk shows in the issue list and
  not only in the notes.

### 5. Low: `run rainbow --max-watts 500` is refused, though its default map is the golden rings arrangement

- **Where:** `src/pewpew/__main__.py:312-313` and `:126`. `rig` stays None when `--map` is omitted,
  but `patterns/__init__.py:37-52` compiles the golden rings as Rainbow's default map.
- **Evidence:** the command prints `--max-watts needs an arrangement map (--map rig.json) for its
  power model`.
- **Fix:** keep the compiled rig for a gallery default that is an arrangement, or say in the error
  that `--map` is needed.

### 6. Low: the CLI accepts a `--max-watts` the file format refuses

- **Where:** `src/pewpew/power.py:42` checks only that the value is finite and over 0. The
  arrangement caps it at `MAX_CAP_W = 1e6` (`models.py`).
- **Evidence:** `PowerCap(5e9)` is accepted. It does no harm, because such a cap caps nothing, but
  the two paths validate differently.
- **Fix:** check `MAX_CAP_W` in `PowerCap.__post_init__`.

### 7. Low: `uncappedWatts` is not reset when the socket closes

- **Where:** `web/src/session/client.ts:208-213` resets `watts: null` but not `uncappedWatts`.
  Verified by reading the code.
- **Effect:** only the `watts !== null` guard in `ReportPanel.tsx:458` hides the stale value.
- **Fix:** add `uncappedWatts: null` to the close reset.

### 8. Low: the contract cites a report that is not in the commit

- **Where:** `docs/studio/contracts.md:79` cites `docs/studio/reports/power-cap.md`.
- **Evidence:** `git ls-tree d5b81d6 docs/studio/reports/` lists no power-cap file. The table at
  `contracts.md:20` says each workstream writes its own report, so the file may still be pending.

## Unverified or not confirmed

- **Max watts commits on every keystroke** (`ReportPanel.tsx:378-387`, from the skill's pass). This
  is mostly mitigated: compile is debounced 200 ms (`web/src/api/queries.ts:8`), bind 250 ms
  (`client.ts:26`), and undo history coalesces on the key `"power"`. Only slow typing or
  backspacing compiles an intermediate cap such as 5 W. `min={1}` against the schema's `> 0` means
  values between 0 and 1 cannot be typed. A browser run would confirm this.
- **`getattr(rig, "limiter", None)` at `app.py:266` is dead code (from the skill's pass): not
  confirmed.** `compile_fn` is injectable, and `FakeRig` in `tests/test_studio.py` has no
  `limiter`, so the tests use this guard. The comment at `app.py:271` is slightly wrong: a rig with
  no power model is still brightness-capped. A rig with no model and `max_watts` would raise, but
  the real `compile_rig` always builds a model.
- **Report sizing and limiter budgets are computed separately** (`electrical.py:229-238` against
  `power.py:176-177`). They agree today: a probe found a per-PSU difference of at most 5.7e-14 W
  across 4 caps. This is a maintainability concern only.
- **`is_flat` repeats catalog lookups** in `Site.capped_a` (`electrical.py:249-253`). Compiling the
  golden rings takes 6.1 ms, so the cost is not measurable. Cleanup only.
- **`limit_stage` can raise inside `PacedLoop`** (`power.py:208-212`), which breaks the "must never
  raise" rule in `pace.py:19-21`. Its only raise is a frame-shape mismatch, which `__main__` cannot
  hit, because the model and the mapping come from the same rig.

## Checked and sound

- **Cap arithmetic:** `scale = min(b, (mw − flat)/variable)` is never over 1, and it is 0 under the
  flat draw. The limiter never brightens display bytes, because `clean` and `to_display_u8`
  sanitize the same way (`power.py:66-71`, `sinks/base.py:82-91`).
- **Spec figures:** 0.184 gives 226.1 W on 1 PSU, and 500 W gives 2 PSUs. Fuse, connector and drop
  use the full-white current, and PSU room uses the capped load (`wiring.py:321-339`).
- **Report arithmetic:** `capped_w` and the per-PSU watts match the limiter budgets exactly.
- **Invalid caps:** NaN, inf, bool and string values in the `power` block are refused at load.
  `PowerCap` rejects NaN and inf, and NaN or inf in a frame is cleaned.
- **Threading:** `_limiter` is written only on the loop thread, and the limiter does not change
  after it is built.
- **Determinism:** the limiter is pure. An uncapped limiter returns the same frame object, so the
  goldens are unchanged.
- **Protocol:** a power message without `uncapped_watts`, from an older server, falls back to
  `watts` (`protocol.ts:118-125`). Older clients ignore the new field.
- **Round trip and share links:** `setPower` drops the default fields and the empty block, and
  `asArrangement` passes `power` through. The save path stores the raw JSON (`app.py:357`), so the
  share ids of uncapped rigs do not change.
- **Format:** the schema is regenerated and its staleness test passes. A v1 file without the block
  loads.
- **ADR amendment:** it cites S413, S645 and S418, with rejected alternatives. The S645 line ranges
  match the pinned excerpt `research/excerpts/S645-abl-power-limiter/bus_manager.cpp`.

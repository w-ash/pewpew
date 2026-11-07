# Review: compact report panel (d9a0717)

Reviewer: a sonnet agent; checks run inline (simplify, then code-review at high effort). Gates pass: `pnpm check`, `pnpm test`, `pnpm e2e`.

## Simplify changes

None. No duplicated formatter in `web/src`; the repeated `<Disclosure><ul>` blocks and the twice-computed PSU rows are small and were left.

## Code review findings

Verified:
1. `display` formatted basis values to 2 decimals, so 0.004 showed "0". Fixed: 6 significant digits.
2. Feed rows dropped `FeedReport.note`. Fixed: the note is appended to the row note. `fuse_window_a` is still not shown (by design).
3. `target_fps`, `limits` and `controllers[]` are not shown; "outputs used" is `outputs.length`, correct because `outputs` lists the slices in use. No change.

Unverified, from reading:
4. The BOM key used `kind:name` while `BomLine` also has `item`. Fixed: key is `kind:item`. Identical note strings or hop keys could still collide; not changed.
5. The "(from the last good compile)" label marks only the Summary heading; Issues and Details carry none. Not changed.

No field-name mismatches with `RigReport` in `src/pewpew/rig/electrical.py`.

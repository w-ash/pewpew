# ws1b review fixes

Fixes for `docs/studio/reports/reviews/ws1b-code-review.md`, on top of the simplify pass
(`ws1b-simplify.md`). Code is in `src/pewpew/rig/geometry.py` and tests in
`tests/test_rig_geometry.py`. Line numbers are at commit 52f1a2b. Each new test fails on the
pre-fix `geometry.py` and passes now.

## Findings

1. **Fixed.** Positions are rounded to 1 nm and normal components to 1e-6 before the float32 cast
   (`geometry.py:65-66, 316-317, 325`). Tests: `test_digests_are_pinned` (`:142`) and
   `test_last_bit_differences_do_not_reach_the_bytes` (`:147`). The second test moves every
   `np.arccos` result and every manifold3d position by one ulp, in each direction, and requires
   the same bytes. The digests are below.
2. **Partly fixed.** An attachment is meshed on every host that accepts it, and it builds when all
   hosts give the same meshes, for example a second bar length (`geometry.py:139-160, 192`).
   Hosts whose meshes differ raise a `GeometryError` that names both. Tests:
   `test_an_attachment_builds_on_hosts_that_mesh_it_alike` (`:376`) and
   `test_an_attachment_refuses_hosts_that_mesh_it_differently` (`:384`). **Skipped:** one GLB per
   (attachment, host) for hosts with different profiles. That changes the contract
   (`contracts.md`, "Geometry"), so ws1, ws3 and ws4 must agree on it first.
3. **Fixed.** A type with no parts raises `GeometryError` (`geometry.py:150`). Test:
   `BAD_DATA["no parts"]`.
4. **Fixed.** The corner-pair sum runs in steps of `PAIR_CHUNK` pairs (`geometry.py:61, 368`).
   Every pair of one corner falls in one step, in the same order, so the bytes do not change. On
   a 4000-point polygon tapered to 0, the traced numpy peak falls from 1228 MB to 10.7 MB. Tests:
   `test_the_chunked_normal_sum_gives_the_same_bytes` (`:161`) and
   `test_normals_memory_stays_bounded_at_a_fine_cone_apex` (`:167`). On the old code, the second
   test peaks at 311 MB.
5. **Fixed.** These now raise `GeometryError`: `taper_to < 0` (`:256`), box sizes `<= 0`
   (`:272`), rect sizes `<= 0` (`:217`) and circle diameters `<= 0` (`:222`). A position beyond
   the float32 range (`:316`) also raises, in place of the `json.dumps` `ValueError`. The ws1
   catalog check already rejects `span_m <= 0` (`catalog.py`, `_check_assembly`). Tests: the
   `BAD_DATA` cases (`:402`).
6. **Fixed.** `SMOOTH_ANGLE_DEG` is now 15° (`geometry.py:58`). Its comment names the smallest
   crease in the bundled meshes. That crease is 28.1°, where the plug's wall meets its flat foot.
   The other crease angles measured are 39.4° and 39.1° (diffuser and cone outer edges), and the
   largest facet angle is 3.75°. The plugs' flat feet now have exact −z normals. The cone's apex
   corners average fewer faces. The shapes do not change. Test:
   `test_flat_feet_have_flat_normals` (`:248`), which fails for any threshold above 28.1°.
7. **Skipped.** The eye's blade is ws1 data (`eye-v0.json`), and changing it changes the drawn
   geometry. The maintainer decides whether the eye stays inside the diffuser outline. The prototype's
   eye also overhangs.
8. **Skipped.** The strip and LED placement is ws1 data (`clen-rgbw-bar-1m.json`), and changing
   it changes the drawn geometry. The plug depth waits on Q-012.
9. **Fixed in geometry.** A profile part with `at` or `at_pixels` raises `GeometryError`
   (`:251`). So does a box part with `range_m`, `taper_to` or an explicit `axis` (`:269`). Tests:
   the five `BAD_DATA` "on a profile/box part" cases. Rejecting these at catalog load
   (`Part._shape`, `models.py`) is for ws1 to decide.
10. **Fixed.** The tests above, plus an assertion that each side face of the cone has its own apex
    vertex (`test_point_is_a_cone_on_the_host_profile`, `:344`). The old comment's claim that each
    apex vertex has "that face's normal" is gone.
11. **Partly fixed.** Geometry's two copies of the pixel rule now share `_pixel_axis`
    (`geometry.py:285, 293`). The LED boxes are placed from the same axis that the GLB publishes,
    and the bytes do not change. **Skipped (other owners):** the second build is in ws3's
    `_assembly` (`src/pewpew/studio/app.py:192`), which should hash the bytes that `build_glb`
    returns. The copy at `compile.py:72` is ws1's. `test_bar_leds_sit_at_the_pixel_positions`
    catches drift between them.

## Cross-platform digests

`assembly_digest` with numpy 2.4.6 and manifold3d 3.5.4. The Linux runs used
`ghcr.io/astral-sh/uv:0.13-python3.14-trixie-slim` with `uv run --frozen --all-extras` on a copy
of the tree without `.venv`. The x86_64 container ran under emulation on an Apple-silicon host.

| type | before, macOS arm64 | before, Linux arm64 | after, all three platforms |
|---|---|---|---|
| clen-rgbw-bar-1m | 469636d5abe8e36c | 469636d5abe8e36c | b0c0e942081d867f |
| clen-360-tube-1500 | 670903ad5ca37a8d | b38e8a6ec9cb6b50 | 62efbd86ef6eeea1 |
| point-v0 | cb485cb4432c07f5 | cb485cb4432c07f5 | 30ba296fe9412539 |
| eye-v0 | 18713c05317365d3 | 78ab9ac032742637 | e30716ce61f71662 |

"All three platforms" means macOS arm64, Linux arm64 and Linux x86_64, which give the same four
digests. `DIGESTS` in `tests/test_rig_geometry.py` pins them.

Gate: `uv run --all-extras --all-groups pytest`, 468 passed, 2 xfailed.

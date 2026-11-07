# Code review of the ws1b geometry builder (high effort)

- **Reviewer:** an independent agent (Opus), not the author. It ran the `code-review` skill at
  high effort, checked each skill finding with its own runs, and changed or dropped the ones it
  could not back up (see the end).
- **Target:** `git diff studio...studio-ws1b-geometry` is empty, because studio has already merged
  the branch (91587e6). So the review covers the branch's own commits, `75ff03b..eb858ef`:
  `src/pewpew/rig/geometry.py`, `tests/test_rig_geometry.py` and `pyproject.toml`. `geometry.py`
  and its tests are the same on studio (ed6032d).
- **Verdict:** the four bundled GLBs are valid glTF 2.0 and match the drawing. The worst defect is
  that the bytes, and so the digests, differ between macOS and Linux.
- **Runs:** `uv run --all-extras --all-groups pytest` passes. The probe scripts were in the
  session scratchpad and are not committed.

## Findings, most severe first

**1. The GLB bytes depend on the platform.** CONFIRMED, medium
- **Where:** `src/pewpew/rig/geometry.py:304`, which breaks the claim at `:7` ("The same inputs
  give the same bytes").
- **Defect:** the corner-angle weights come from `np.arccos`, and its float64 result differs in
  the last bits between macOS and Linux. Those bits reach the float32 normals.
- **Scenario:** the ws1b source was built with numpy 2.4.6 and manifold3d 3.5.4 on two arm64
  machines: macOS, and Linux in the `pewpew:local` image. The tube and the eye get different
  digests on each (`670903ad…` and `b38e8a6e…` for the tube, `18713c05…` and `78ab9ac0…` for the
  eye). The bar and the point match. Positions and indices are identical. Only normals differ: 8
  vertices of each tube cap and 6 of the eye, all at the circle's axis extremes, where a component
  of about 2e-17 changes (p7_parts.py). Step by step (p8_raw.py), manifold3d's float64 output, the
  cross products and the cosines are identical. Only the `arccos` result differs. Hence the
  macOS test suite and the Linux server or CI never produce the same bytes. A pinned golden
  digest would fail on one platform, and the contract's "deterministic bytes"
  (`docs/studio/contracts.md:79`) holds only on one machine. The author's report calls this
  untested and suspects sin and cos (`docs/studio/reports/ws1b-geometry.md`, "Platforms"). The
  cause is `arccos`. That numpy calls each platform's libm `acos` here is an inference.
- **Fix:** round the normals before the cast. With `np.round(normals, 6)` (or with weights that
  need no transcendental function) the macOS and Linux arm64 digests agree on all four types
  (p9_fix.py). x86_64 was not tested. Then add a test that pins the four digests, and run it on
  Linux too.

**2. An attachment can have only one host type in the whole catalog.** CONFIRMED, medium (latent)
- **Where:** `src/pewpew/rig/geometry.py:165-174`.
- **Defect:** `_host_scope` returns a host only when exactly one fixture type has an anchor that
  accepts the attachment's `fits`. Otherwise every `host:` part raises `GeometryError`. But
  `compile_rig` accepts the same attachment on any host that has the profiles
  (`src/pewpew/rig/compile.py:189-203`).
- **Scenario:** a second bar length that reuses `diffuser_outer` on its end anchors makes
  `build_glb("point-v0")` and `build_glb("eye-v0")` raise. The branch's own test does this with a
  copied bar (`tests/test_rig_geometry.py:298-306`). Studio's `_assembly` catches the
  `ValueError` and serves both attachments with `assembly_url: null`
  (`src/pewpew/studio/app.py:188-195` on studio). Compiles still pass, but the 3D view has no
  mesh for the point or the eye on any bar. That the viewer then draws nothing for them is an
  inference. Two hosts whose profiles differ also could not share one GLB at all. The author's
  report lists this as open.
- **Fix:** key attachment assemblies by (attachment, host type): `build_glb(att_id, catalog,
  host=…)`. Then give each `attachment_matrices` entry, or the catalog entry, the matching URL. This
  changes the contract (`contracts.md:78-82`), so ws1, ws3 and ws4 must agree.

**3. A fixture type with no parts gives an invalid glTF.** CONFIRMED, low
- **Where:** `src/pewpew/rig/geometry.py:358-360, 411`, reached from `build_glb` (`:117-124`).
- **Defect:** `FixtureType.parts` and `AttachmentType.parts` default to `[]`
  (`src/pewpew/rig/models.py:249, 267`), and the catalog accepts that. The writer then emits
  `children: []`, `meshes: []`, `accessors: []`, `bufferViews: []`, `materials: []`, a
  zero-length BIN chunk and `buffers[0].byteLength: 0`.
- **Scenario:** a new fixture type written without `parts` loads. The Khronos validator
  (2.0.0-dev.3.10) gives its GLB 6 errors (`EMPTY_ENTITY` on five arrays, `VALUE_NOT_IN_RANGE` on
  `byteLength`) and the info `GLB_EMPTY_BIN_CHUNK`. The spec makes those arrays `[1-*]`, with
  `byteLength >= 1`
  ([glTF.meshes](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#_gltf_meshes),
  [node.children](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#_node_children),
  [buffer.byteLength](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#_buffer_bytelength)).
  It also says the empty BIN chunk SHOULD be omitted
  ([binary buffer](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#binary-buffer)).
- **Fix:** raise `GeometryError("… has no parts")` in `part_meshes`, or make the catalog require
  at least one part on an assembly type.

**4. The normals step uses memory quadratic in a vertex's valence.** CONFIRMED, low
- **Where:** `src/pewpew/rig/geometry.py:314-321`.
- **Defect:** `_corner_normals` builds every ordered pair of corners at each vertex, k² pairs for
  k triangles. A cone apex (`taper_to: 0`) has one triangle per profile vertex. Circles are capped
  at 96 segments, but `polygon` has no limit on its point count.
- **Scenario:** a 4,000-point polygon with `taper_to: 0` builds in 0.5 s at 1.3 GB peak RSS. At
  2,000 points it is 0.14 s and 385 MB, and without the taper 4,000 points take 99 MB (p4_scale.py).
  Each doubling of the point count multiplies the memory by about 3. Studio builds every GLB when it loads the
  catalog, so a finely traced profile can take down a small server at startup.
- **Fix:** accumulate per vertex group in chunks, or cap the polygon's point count in the catalog
  check and raise `GeometryError` above it.

**5. Degenerate dimensions build a GLB without error.** CONFIRMED, low
- **Where:** `src/pewpew/rig/geometry.py:227` (`taper_to`), `:238-239` (box sizes), `:191` (rect
  sizes).
- **Defect:** none of these values is range-checked. The `no area` guard (`:274-276`) catches only
  shapes that lose every triangle.
- **Scenario (p3_robust.py):**
  - `taper_to: -1` builds an 8.5 kB part whose far end is mirrored through the axis, so the solid
    crosses itself.
  - `box: [0.01, 0, 0.01]` and `rect: [0, 0.01]` each build two coincident faces that z-fight.
  - `pixels.span_m: 0` builds 64 coincident LED boxes, and a negative span builds as well. Then
    `pixel_axis.span <= 0`, which the viewer's `pixelAxisOf` rejects.
  - A `range_m` of 1e300 fails in `json.dumps` with "Out of range float values are not JSON
    compliant" rather than a `GeometryError`.

  Zero or negative circles, empty or collinear polygons and a non-increasing `range_m` are
  rejected correctly.
- **Fix:** in `_part_solid`, require `taper_to >= 0`, every box and rect size `> 0`, and finite
  results. Have the catalog check require `span_m > 0`.

**6. The 30° crease smooths the plug's flat edge.** CONFIRMED, low
- **Where:** `src/pewpew/rig/geometry.py:47-51`.
- **Defect:** the comment checks only the outer edge, at 38° (acos(11.9/15.1)). The plug's
  profile, `diffuser_inner`, meets the flat at acos(11.9/13.6) = 28.96°, which is under 30°.
- **Scenario:** all six corner normals of the plug's flat bottom (`point-v0` and `eye-v0`) point
  14.06° off −z instead of straight down (p2_shape.py). That face sits inside the bar, so the
  visible effect is small. Any future profile corner between 3.75° and 30° shades as rounded.
- **Fix:** lower the threshold to about 15°. That is still above the facet angle, and the
  facet-to-flat junction stays sharp. Fix the comment to name the smallest crease.

**7. The eye's blade overhangs the diffuser.** CONFIRMED (geometry), low. It is ws1 data, and it
copies the prototype.
- **Where:** `src/pewpew/rig/data/attachment_type/eye-v0.json:11-12` (`blade_w` 30 mm, `blade_t`
  20 mm).
- **Defect:** the blade is a 30 × 20 mm rectangle at the bar's end. Its corners reach 18.03 mm
  from the axis, against the diffuser's 15.1 mm radius. 44 mm² of its 600 mm² cross-section lies
  outside the diffuser outline, and the diffuser end above and below it is bare (p2_shape.py). The
  brief and `domain-model.md:254` ask for attachments flush on the outer profile. The prototype's
  eye also overhangs (`golden-tubes-3d.html:355-374`).
- **Fix:** ask the maintainer whether the eye should stay inside the diffuser outline. If so, make the
  half-width at most √(15.1² − (blade_t/2)²), which is 11.3 mm at 20 mm thick, or add a short
  `host:diffuser_outer` collar.

**8. The strip and the LED bodies sit inside the housing.** CONFIRMED (geometry), low. It is ws1
data.
- **Where:** `src/pewpew/rig/data/fixture_type/clen-rgbw-bar-1m.json:46-47`, and the plug depth
  at `point-v0.json:10` and `eye-v0.json:10`.
- **Defect:** the strip is at `-flat_z - strip_t/2`, so it spans z −12.9 to −11.9 mm. That is
  wholly inside the housing (top face at −11.9 mm), with its top face coplanar with the housing's
  top. The LED boxes span −12.7 to −11.1 mm, half buried. The 15 mm plug also passes through the
  end LEDs, which sit 5.3–10.3 mm from each end.
- **Scenario:** the bar's open diffuser ends show a z-fighting strip on the housing top. The
  LEDs stand 0.8 mm proud instead of 1.6 mm. The diffuser is drawn opaque (no
  transparency in `web/src/viewer` on studio-integration), so this shows only from the ends. The
  author's report notes the LED and strip placement.
- **Fix:** put the strip at `-flat_z + strip_t/2` and give `leds` an `at` of
  `[0, 0, "strip_t + led_h/2"]`. Or keep the bodies on the face but move the strip. Settle the
  plug depth with Q-012.

**9. Shape fields that don't apply are ignored without an error.** CONFIRMED, low
- **Where:** `src/pewpew/rig/geometry.py:223-248`.
- **Defect:** a profile part ignores `at` and `at_pixels`. A box part ignores `range_m`,
  `taper_to` and `axis`.
- **Scenario:** `"at": [0, 0, 5]` on a profile part builds the same bytes as no `at` (p3_robust.py).
  An author who moves a profile part with `at` sees no change and gets no error.
- **Fix:** reject them in `Part._shape` (`models.py:170-176`), or raise `GeometryError` here.

**10. The tests can't catch findings 1, 3 or 6.** CONFIRMED, low
- **Where:** `tests/test_rig_geometry.py:109-113, 168-178, 276`.
- **Defect:**
  - Determinism is checked only within one process. No digest is pinned, so the macOS and Linux
    split in finding 1 passes.
  - The normals test bounds each corner by `SMOOTH_ANGLE_DEG` itself, so a wrong threshold
    (finding 6) cannot fail it.
  - Nothing tests the `GeometryError` paths or an assembly with no parts.
  - The comment at `:276` says the apex has one vertex per side face with that face's normal, but
    the test asserts only that the apex position is unique.
- **Fix:**
  - Pin the four digests.
  - Assert that the plug's and the diffuser's flat faces have exact −z normals.
  - Add parametrized `GeometryError` cases for the inputs in findings 3 and 5.

**11. Each GLB is built twice per catalog load, and the pixel rule has three copies.** CONFIRMED,
cleanup
- **Where:** `src/pewpew/rig/geometry.py:127-129`, called next to `build_glb` at
  `src/pewpew/studio/app.py:192` on studio. The pixel rule is at `geometry.py:121`, `geometry.py:256`
  and `src/pewpew/rig/compile.py:72`.
- **Defect:** `assembly_digest` rebuilds the GLB only to hash it. The rule
  `-span/2 + (j+0.5)·span/n` is written three times.
- **Fix:** have the callers hash the bytes `build_glb` returns. Put the pixel rule in one helper,
  for example `FixtureSpec.pixel_y()`.

## Skill findings changed or dropped

- **Changed.** The skill said a second host makes `/api/catalog` return a 500. On studio the
  `_assembly` call catches `ValueError`, so the endpoint stays up and the effect is a null URL
  (finding 2).
- **Changed.** The skill said every request rebuilds the GLBs. On studio they are built once per
  catalog load, and twice each (finding 11).
- **Dropped.** The skill said `pytest.importorskip` silently skips the geometry tests. On studio,
  `pyproject.toml` has `dev = ["pewpew[dev,studio]"]`, so `uv run pytest` installs manifold3d.
- **Dropped.** The skill's finding on the wording of the author's report. It is out of scope.

## Checked and sound

- **GLB container**, per the
  [binary glTF layout](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#binary-gltf-layout).
  A stdlib-only parser (p1_glb.py) found these correct:
  - the magic, the version and the total length
  - JSON first and BIN second, each 4-byte aligned
  - JSON padded with spaces and BIN with zeros
  - BIN no more than 3 bytes longer than `byteLength`
  - buffer 0 with no `uri`, every accessor offset a multiple of 4, and each view with its target

  The Khronos validator 2.0.0-dev.3.10 gives all four bundled GLBs 0 errors, 0 warnings, 0 infos
  and 0 hints.
- **Accessors.**
  - POSITION `min`/`max` equal the float32 data exactly.
  - Normals are unit to within 4e-8.
  - Every part has positive signed volume, with no face whose corner normals point inward, so the
    winding is counter-clockwise outward
    ([instantiation](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#instantiation)).
  - Indices are `UNSIGNED_INT`, in range, and in a multiple of 3.
  - Data is written little-endian (`newbyteorder("<")`), and the JSON uses sorted keys with
    `allow_nan=False`.
- **Same-platform determinism.** Digests are identical across 5 processes (`PYTHONHASHSEED` 0, 1,
  12345 and random, and with single-thread env vars). Python float `repr` and `sort_keys` are
  platform independent, and manifold3d's float64 output matched between macOS and Linux.
- **The bar against the drawing.**
  - The housing is 18 × 18.5 mm (x ±9, z −30.4 to −11.9 mm), and the T-slot is open at the base.
    Rays find the 8 mm opening, the 1.5 mm lips and the cavity ceiling at −25.9 mm.
  - The 30.2 mm diffuser has its flat at −11.9 mm, with an 18.6 mm chord, sitting on the housing
    top.
  - The overall height is 45.5 mm (−30.4 to +15.1 mm).
  - The origin is on the diffuser axis, and +y runs from the `in` anchor to `out`.
  - The pixels face +z into the diffuser.
  - Housing volume is 279.7 cm³, which equals 0.992 m × 282 mm².
- **Attachment frames.** Meshing in the pinned frame (`contracts.md:68-71`, `pose.py:160-174`) is
  right:
  - the cone's base ring is a subset of the diffuser's end ring
  - the apex is on the axis at the `tip` anchor
  - the plug runs y −15 to 0 mm into the bore
  - the eye's slot is cut right through (a ray at x 0.3 mm, y 50 mm hits nothing)
  - the end_a frame is Rz(180°), which suits the x-symmetric profile

  ws4's viewer turns the attachment's local y into the host's y through the host-local matrix
  (`web/src/viewer/instances.ts:200-226` on studio-integration).
- **Glow metadata.**
  - `glow` and `gain` match the catalog on every part: 0.25 on the point and eye parts, and 1.0 on
    the diffuser and tube.
  - `pixel_axis` is {y0 −0.5, span 1.0, count 64} for the bar and {−0.73, 1.46, 36} for the tube,
    the same formula as `compile.py:72`, and null on attachments.
  - LED box centres equal `compile_rig`'s pixel positions.
- **Robustness that holds.**
  - Unknown or wrong-kind ids raise `KeyError`.
  - A `range_m` that does not increase, a zero or negative circle, an empty, two-point, collinear
    or sliver polygon, a shape cut away to nothing, a sub-micron part and `at_pixels` on an
    attachment raise `GeometryError`.
  - NaN and infinite values are refused by the models.
  - Profile cycles are refused by the catalog, so the recursion ends.
  - A 20,000-pixel `at_pixels` part builds in 0.65 s.

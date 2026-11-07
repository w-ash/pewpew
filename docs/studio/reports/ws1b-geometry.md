# ws1b: geometry

**A design figure is wrong.** Design §8 item 11 gives the bar's GLB bounds as x ±9 mm
(`docs/studio/domain-model.md:367`). That is the 18 mm housing. The 30.2 mm round diffuser is
wider, so the whole bar spans x ±15.1 mm. The drawing shows the diffuser wider than the housing
(Clen's diffuser dimension drawing, not public).
The z bounds hold: axis_z = 45.5 − 30.2/2 = 30.4 mm, so the base is at −30.4 mm and the diffuser
top at +15.1 mm (arithmetic). `test_bar_bounds` checks ±15.1 mm for the whole bar and ±9 mm for
the housing and caps.

Workstream 1b built `src/pewpew/rig/geometry.py`. `build_glb(type_id, catalog) -> bytes` meshes
every part of a fixture or attachment type with manifold3d and writes a deterministic GLB with its
own writer. `assembly_digest(type_id, catalog) -> str` returns the URL key. `manifold3d>=3.5.4` is
in the new `studio` extra, imported lazily. `tests/test_rig_geometry.py` has 22 tests, skipped
without manifold3d. `uv run pytest` gives 333 passed and 2 xfailed in 2.4 s.

## What the GLB holds

- **Frames.** A fixture is meshed in the fixture-local frame of design §3
  (`docs/studio/domain-model.md:177-183`). An attachment is meshed in its own frame, the one pinned
  in `docs/studio/contracts.md:68-71`. The file uses these frames unchanged. glTF is
  right-handed, +y up, in meters
  ([§3.4](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units)).
- **Nodes.** Node 0 is the root, named after the type, and its children are the parts in data
  order. Each part is one node and one mesh with one triangle primitive: POSITION, NORMAL and
  uint32 indices.
- **Part extras** are `{"glow", "gain", "part"}`.
- **Root extras** are `{"pixel_axis": {"y0", "span", "count"}}` for a fixture type, with
  y0 = −span/2. Pixel j is at y0 + (j + 0.5)·span/count, the same formula as
  `src/pewpew/rig/compile.py:72`. For an attachment type `pixel_axis` is null (see Deviations).
- **Materials.** There is one material per `finish` in use, sorted by name. A part with no finish
  gets one named `unspecified`. An unknown finish name gets a neutral grey, so a new fixture still
  needs no code. The values are in `FINISHES` (`src/pewpew/rig/geometry.py:59`):

  | finish | linear base colour | metallic | roughness | source |
  |---|---|---|---|---|
  | aluminum | 0.916, 0.923, 0.924 | 1 | 0.35 | colour: "Aluminum" at https://api.physicallybased.info/materials; roughness by eye |
  | black | 0.05 | 0 | 0.5 | "Toner (Black)", same API |
  | black-anodized | 0.05 | 1 | 0.45 | the toner grey, made metallic by eye |
  | opal | 0.8 | 0 | 0.6 | by eye |
  | unspecified or unknown | 0.5 | 0 | 0.5 | by eye |

  The API labels its toner colour as linear sRGB. That its other colours are linear too is an
  inference.

**Sizes.** These are file sizes and build times on this Mac: bar 81,760 B in 14 ms, tube
57,860 B in 4 ms, point 21,092 B in 2 ms, eye 36,400 B in 3 ms.

## Decisions

1. **The normals are computed here, not by manifold3d.** Each triangle corner gets the
   angle-weighted mean of the face normals at its vertex that lie within 30° of its own face
   (`_corner_normals`, `src/pewpew/rig/geometry.py:290`). Then equal (position, normal) pairs
   merge. Two observed manifold3d 3.5.4 behaviours ruled out `calculate_normals`:
   - It gives the cone apex one vertex, with its normal along the axis. Every side triangle runs
     from the base to the apex, so the cone would shade as a gradient along its length. Here the
     apex gets one vertex per side face, each with its own normal (77 for the point).
   - After a reflecting `Manifold.transform` (the y↔z swap), `calculate_normals` returned normals
     perpendicular to their faces. I did not look for an upstream issue.
2. **The 30° crease** is above the 3.75° between circle facets and below the 38°
   (acos(11.9/15.1)) between the diffuser's outer wall and its flat foot, so that edge stays
   sharp.
3. **Extruding along y.** manifold3d extrudes along its z. For `axis: "y"` the code swaps the y
   and z columns in numpy and reverses the winding, which keeps the triangles counter-clockwise
   seen from outside. `test_parts_are_closed_solids_with_outward_normals` checks this on every
   part: a closed solid, positive volume, and every corner normal within 30° of its face.
4. **There are no 3D booleans.** manifold3d does the 2D CSG (`CrossSection`), the circles, the
   extrusion and one cube. The `at_pixels` boxes are copies of one cube mesh at the pixel
   centres. With no 3D boolean, nothing can depend on parallel boolean order.
5. **The circles have 96 segments.** manifold3d puts vertex i at 360·i/n degrees and computes it
   with degree-exact sin and cos
   ([cross_section.cpp L348-L360](https://github.com/elalish/manifold/blob/v3.5.4/src/cross_section/cross_section.cpp#L348-L360)).
   A multiple of 4 therefore puts a vertex exactly on each axis extreme, so the bounds come out
   exact. Facets are 3.75° apart, and at 15.1 mm the vertices are at most
   r(1 − cos(π/96)) ≈ 8 µm from the true circle (arithmetic). Away from the vertices the surface
   lies up to about 12 µm inside, and the tests allow 20 µm there.
6. **Profile coordinates.** The primitive is centred at `at`. The shapes in `minus` use the same
   coordinates and are not offset by the parent's `at`. The bar's slot entries need this: they
   give absolute heights such as `lip_t/2 - axis_z`
   (`src/pewpew/rig/data/fixture_type/clen-rgbw-bar-1m.json:29-36`). `polygon` uses the NonZero
   fill rule, so either winding works. No data uses polygons yet.
7. **`taper_to`** goes to manifold3d's `scale_top`, applied at the `range_m[1]` end, so the cone
   apex is on the profile origin at the far end
   ([manifold3d.cpp L453-L462](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/manifold3d.cpp#L453-L462)).
   The point's apex is at exactly (0, 0.1, 0), its tip anchor.
8. **The host of an attachment** is the one fixture type with an anchor whose `accepts` equals
   the attachment's `fits`. Host profiles are evaluated with the host's dims. When there are zero
   such hosts or several, a part that names `host:` raises `GeometryError`
   (`test_host_profiles_need_exactly_one_host`).
9. **The digest** is the first 16 hex digits of the SHA-256 of the GLB bytes. Because it hashes
   the bytes, a URL and its bytes always agree, and no builder version is needed.
10. **The writer** sorts JSON keys, writes no generator or timestamp, and pads JSON with spaces and
    BIN with zeros. Every array has its own buffer view, so no view needs a byteStride. POSITION
    min and max are the exact float32 values, as
    [§3.6.2.5](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#accessors-bounds)
    requires.
11. **Errors.** An unknown id, or an id of another kind, raises `KeyError`. Data that cannot be
    meshed raises `GeometryError(ValueError)`: a `range_m` that does not increase, an empty part,
    `at_pixels` on an attachment, or a missing host or host profile.

## Deviations from the design and contracts

- **Bar bounds**: x ±15.1 mm, not ±9 mm (top of this report).
- **`pixel_axis` is null on attachments.** One attachment GLB serves both ends. Through the frame
  at `end_a`, which is Rz(180°) (`src/pewpew/rig/pose.py:161-175`), host y = −y − L/2. At `end_b`,
  host y = y + L/2. One axis cannot describe both. The browser should give an attachment's
  `pixels` parts the colour of the end pixel they sit on: pixel 0 at `end_a` and n − 1 at
  `end_b`. That is the clamp rule of `docs/studio/domain-model.md:252-254`.
- **`at` with `at_pixels`** is an offset from each pixel. `Part` says nothing about the two
  together (`src/pewpew/rig/models.py:150-155`). No data sets both.
- **The LED bodies sit half inside the housing.** Each body is centred on its pixel, at
  z_m = −11.9 mm, which is the housing's top face, so it spans −12.7 to −11.1 mm. This follows
  `models.py:152-154`. If a body should sit on the strip, ws1 can add `"at": [0, 0, "led_h/2"]`
  to the `leds` part (`clen-rgbw-bar-1m.json:47`). The strip likewise sits inside the housing
  (−12.9 to −11.9 mm), as the design places it (`domain-model.md:89`). Both stay hidden inside the
  opaque diffuser.

## Open issues

- **ws3.** `assembly_digest` builds the GLB, so cache the bytes by `(catalog.digest, type_id)`
  and build each type once.
- **ws4.** Use the attachment colour rule above. `pixel_nearest` needs nearest sampling at
  u = (y − y0)/span. Each LED box spans y_j ± 2.5 mm inside its own texel.
- **Platforms.** Byte identity is tested within one process and across processes (identical
  digests under `PYTHONHASHSEED` 0, 1 and 12345). It is not tested between macOS and the Linux
  container. Platforms might differ in the last bit of sin and cos (inference). The URL would
  still match the bytes it serves.
- **Asymmetric hosts.** At `end_a` an attachment is turned 180° about z, so one built on a host
  profile that is not symmetric in x would be mirrored there. Every current host profile is
  symmetric.
- **Several hosts.** A second fixture type that accepts `diffuser_outer` (another bar length,
  say) makes the host ambiguous, and `build_glb` refuses. Supporting it changes the contract to
  one assembly per (attachment, host) pair.
- **Diffuser seating.** In the beam-angle drawing the diffuser's lower edges seem to run down
  into the housing (Clen's beam-angle drawing, not public;
  inference). The model sets the diffuser on the flat. The Q-011
  measurements settle it (`domain-model.md:371`).
- **Merge.** `pyproject.toml` adds `studio = ["manifold3d>=3.5.4"]`. ws3's `studio` extra
  conflicts with it there and in `uv.lock`. Keep both sets of packages and rerun `uv lock`.

## Validation

- **Khronos glTF validator** 2.0.0-dev.3.10 reports 0 errors, 0 warnings, 0 infos and 0 hints for
  all four GLBs. `npx gltf-validator` fails ("could not determine executable to run") because the
  npm package has no CLI, so I ran it once by hand through its `validateBytes` API. It is not a
  test dependency.
- **The tests** read the GLB with their own parser:
  - the header, the chunk order, lengths, alignment and padding
  - accessor counts, offsets, bounds against the data, index range and unit normals
  - one node and one mesh per part, with their extras and materials
  - each part rebuilt as a manifold3d solid
  - bounds, the flat on the housing (both at −11.9 mm, the flat's chord 18.6 mm), and rays up the
    T-slot: up the middle the first hit is the slot ceiling at −25.9 mm, not the base
  - LED centres equal to `compile_rig`'s pixel positions
  - the tube from data alone
  - the point's apex and its flush base, and the eye's open slot

## Sources

- glTF 2.0 specification, read 2026-10-22:
  - [§3.4 coordinate system and units](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units)
  - [§3.6.1.2 GLB-stored buffer](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#glb-stored-buffer)
  - [§3.6.2.4 data alignment](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#data-alignment)
  - [§3.6.2.5 accessor bounds](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#accessors-bounds)
  - [§3.7.2.1 meshes](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#meshes-overview)
  - [winding order under the node transform](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#instantiation)
  - [§4.4 binary glTF layout](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#binary-gltf-layout), [header](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#binary-header), [chunks](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#chunks-overview)
  - [baseColorFactor is linear](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#_material_pbrmetallicroughness_basecolorfactor)
- manifold v3.5.4 (Apache-2.0, per design §6):
  - [cross_section.cpp L348-L360](https://github.com/elalish/manifold/blob/v3.5.4/src/cross_section/cross_section.cpp#L348-L360) (`Circle`)
  - [constructors.cpp L215-L216](https://github.com/elalish/manifold/blob/v3.5.4/src/constructors.cpp#L215-L216) (`Extrude`)
  - [manifold3d.cpp L453-L462](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/manifold3d.cpp#L453-L462) (the `extrude` binding and `scale_top`)
  - [PyPI](https://pypi.org/project/manifold3d/). `uv.lock` pins 3.5.4 with manylinux x86_64 and aarch64 wheels.
- Materials: https://api.physicallybased.info/materials ("Aluminum", "Toner (Black)"), read
  2026-10-22.
- Validator: the npm package [gltf-validator](https://www.npmjs.com/package/gltf-validator),
  2.0.0-dev.3.10.
- Fixture drawings, kept with the maintainer's fixture notes (not public): Clen's diffuser
  dimension drawing and Clen's beam-angle drawing, both viewed.
- Repo:
  - `docs/studio/domain-model.md:58`, `:89`, `:177-183`, `:245-273`, `:367`, `:371`
  - `docs/studio/contracts.md:68-71`, `:78-82`
  - `src/pewpew/rig/models.py:150-155`
  - `src/pewpew/rig/pose.py:161-175`
  - `src/pewpew/rig/compile.py:72`
  - `src/pewpew/rig/data/fixture_type/clen-rgbw-bar-1m.json:29-36`, `:46-47`
  - `docs/studio/prototype/golden-tubes-3d.html:346-378`, with `point.png` and `eye.png`

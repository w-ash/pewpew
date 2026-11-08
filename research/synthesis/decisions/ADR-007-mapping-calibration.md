# ADR-007: Mapping & calibration — declarative fixtures, Pixelblaze presentation, marimapper import

Status: Proposed (2026-07-03)

## Context

Three coordinate conventions coexist: index/channel space (WLED, FPP,
LedFx), normalized world units (Pixelblaze), and physical coordinates with
transforms (Chromatik `.lxf`). Only pattern engines think in coordinates;
players think in channels. pewpew needs one native format expressive enough
for strips, matrices, volumes, and multi-controller canvases, plus a
calibration path for irregular 3D geometry.

## Decision

- **Native format: declarative JSON fixtures**, Chromatik-shaped —
  components (`points`, `strip` count+spacing, `arc`), nested/parametric
  fixtures, sequential translate/rotate/scale transforms, **physical units
  (meters), y-up right-handed**, per-component output bindings
  (start/reverse/stride/repeat). Masks are first-class named point-subset
  queries (tags/views), not `-1` sentinels. Concepts clean-roomed from the
  documented spec; no LX code.
- **Presentation to patterns: the Pixelblaze way** — normalized 0–1 world
  units with Fill/Contain policy derived at load, plus raw physical coords
  and wiring index. Geometry orientation (transforms) and wiring byte-order
  (reverse/stride) are deliberately separate layers.
- **Runtime: the map compiles to flat NumPy arrays** (index→coord table,
  coord→output-slot gather per sink).
- **Import filters**: WLED `ledmap.json`, Pixelblaze map JSON, marimapper
  `led_map_3d.csv`, xLights `.xmodel` (optional).
- **Calibration: marimapper as the external tool** (separate GPL process;
  pewpew ships a backend + CSV importer, never vendors code). Built-in
  fallbacks: grid/strip generators and click-on-photo manual mapping.

## Consequences

- Patterns are installation-portable (normalized) without losing physical
  scale (raw coords) or index-space compatibility (WLED-style effects).
- The marimapper importer must rescale LED-pitch units to meters from one
  measured spacing and carry per-point reprojection error; its real-world
  accuracy is unquantified upstream — prototype item #7.
- xLights `.xmodel` import is deferred until the prop ecosystem matters.

## Evidence

- [S309] Chromatik `.lxf`: the most expressive open declarative format —
  points/strip/arc, nested transforms, y-up, physical units, raw and
  normalized coords per point, tags/views as masks, per-component outputs.
- [S304][S680:README.mapper.md#L12-L36] Pixelblaze's load-time
  normalization to 0–1 world units with Fill/Contain — the most influential
  portability convention in the hobby space. (Both IDs resolve to the same
  Pixelblaze mapper document — seed URL vs pinned repo copy.)
- [S305][S630:ledfx/virtuals.py#L409-L495] LedFx's precompiled
  segment→device gathers — claimed "up to 13× faster" in a code comment
  only, unbenchmarked in-repo (ledfx.md open questions) — evidence for the
  compiled NumPy runtime representation direction, not for the constant.
- [S303] WLED ledmap: index permutation + width/height + `-1` gaps —
  expressive enough only for import.
- [S300] marimapper: actively maintained (v3.4.2, 2026-03), sequential
  blink + COLMAP SfM, documented custom-backend API.
- [S670:marimapper/file_tools.py#L68-L85] The 3D CSV schema
  (`index,x,y,z,xn,yn,zn,error`; units = median LED pitch; sparse missing
  indices) — the import contract.
- [S670:LICENSE#L1-L5] marimapper is GPL-3.0 — the separate-process
  boundary in ADR-012 applies.
- [S035] LX's license is non-commercial-capped — why the format is
  clean-roomed rather than the code studied for reuse.

## Rejected alternatives

- **Index-permutation as the native format** (WLED/FPP) — geometry-blind;
  no coordinates, units, or 3D [S303][S308].
- **Adopting `.lxf` verbatim / porting LX code** — license risk; concepts
  only [S035][S309].
- **LedFx virtuals as the geometry model** — routing/canvas abstraction,
  not geometry; kept only as the runtime-gather idea [S305].
- **Building a camera mapper before importing marimapper's** — marimapper
  is active with a trivial backend API; Lightwork (the alternative) is dead
  (last push 2019) [S300][S301].
- **Normalized-only coordinates** (pure Pixelblaze) — a "10 cm ripple" is
  inexpressible without physical units [S304][S309].

## Amendment (2026-10-22)

The studio ([ADR-024](ADR-024-hosted-studio.md)) needed a concrete native
format. It is specified in `docs/studio/domain-model.md`; this amendment
records the decisions that bind the engine. The original decision stands:
physical units, y-up right-handed, normalized presentation, NumPy gathers,
marimapper as the external calibration tool. The Chromatik-shaped component
list (`points`, `strip`, `arc`) is superseded for new work by the
arrangement format below; the importers listed above are unchanged.

- **Three layers.** The split follows GDTF (catalog) and MVR (scene)
  [S316]. The **catalog** is hand-written JSON, one file per entity,
  discriminated by `kind` (fixture type, attachment type, chipset,
  connector, cable, PSU, firmware, controller). The **arrangement** is what
  a user or the studio writes: fixtures with poses, preset groups (`ring`,
  `array`), controllers, PSUs, and wiring (explicit or `auto`). **Derived**
  data is never stored: instances, world matrices, the pixel table, output
  slices, auto-wiring, the report. The electrical layer is new design:
  GDTF's `WiringObject` models power sources, consumers and fuses but no
  cable length or gauge [S316]; a survey of other formats found none that
  models PSUs, feeds or cables (`docs/studio/planning/2026-10-22-a4-fixture-model-prior-art.md`, section 6).
  Chromatik keeps geometry, wiring and outputs in one fixture file [S309],
  the mixing this split avoids.
- **Provenance on every value.** A catalog fact is a literal or
  `{"v", "status", "src"}`, with status one of `measured | stated |
  inferred | derived | assumed`. Values are SI floats with unit suffixes.
  Dimensions may be expressions over the entity's `dims`, evaluated in
  Python only. A result that rests on an unmeasured value is reported as a
  warning.
- **Frames: meters, y-up, right-handed; quaternions xyzw.** Rotations are
  stored as quaternions in xyzw order with w >= 0, never as Euler angles.
  glTF uses the same convention: right-handed, +Y up, metres, node rotation
  an XYZW unit quaternion [S527], which lets the server's GLB and the
  compiled matrices agree without conversion. Matrices are exported
  column-major in the order three.js `Matrix4.elements` uses [S523].
- **MVR conversion.** MVR is right-handed, Z-up, 1 unit = 1 mm [S316].
  Import and export convert with a fixed rotation matrix
  C = [[1,0,0],[0,0,-1],[0,1,0]] (det +1, so handedness holds) and a factor
  of 1000; export is `p = 1000*C*p`, `R = C*R*C^T` and import is the
  inverse.
- **Contain normalization, data-order index.** `compile_rig` indexes pixels
  in data order: controller, then output, then chain, then pixel `j`,
  with pixel `j` of `n` at `-span/2 + (j+0.5)*span/n` along the fixture
  axis. It then Contain-normalizes `(p - mid)/max(ptp) + 0.5` to float32
  (Pixelblaze's Contain policy [S304]) and hands the result to
  `Renderer(pattern, mapping)` unchanged. The engine's `index` is
  `arange(N)`, so it follows data order with no change to the ADR-005
  contract. Raw `positions_m` stay available for scale-aware effects, as
  the original decision requires.
  *(Since 2026-11-07: the rig uses the room map's Contain,
  `pewpew.mapping.contain`, over the positions turned into the plan frame,
  `positions_m @ C^T`; a flat axis and a single point map to 0, not 0.5.
  See the amendment "One rig description".)*
- **Versioning.** Files carry `format` and an integer `version`; pure
  `vN -> vN+1` functions migrate on load and a file newer than the code is
  refused. Compile output carries a `catalog_digest` so a stored arrangement
  can say when catalog dimensions changed.

Evidence added: [S316] (GDTF and MVR specifications), [S527] (glTF 2.0
coordinate and quaternion conventions), [S523] (three.js matrix order),
with [S304] and [S309] as before. The conversion matrix, the Contain
formula and the pixel-position formula are pewpew's own design (arithmetic
in `docs/studio/domain-model.md`, sections 3 and 4); no source is cited for them.

## Amendment (2026-10-30) — room map files and fixture units

Pulls a subset of the native format forward from Phase 3 for the three-board
rig (`docs/backlog/v0.2.x.md`, story "Room map file with live 2D
simulation"): 60 straight bars on three stock-WLED boards, a layout that is
final only once the bars are up. Code: `src/pewpew/room.py`; example
`examples/room-60-bars.json`. *(Since 2026-11-05: `src/pewpew/room/map.py`.)*

### Decision

- **Room map file: JSON in meters, straight strips only.** Each fixture has
  `pixels`, a `start` point and either an `end` point or an `angle`
  (degrees) with a `length`, an optional `pitch`, optional `tags`, and its
  output binding: `board`, `output`, `chain` position and `input` end
  ("start" or "end"). `instances` with a `step` vector repeats a fixture as
  an array, stepping its chain position. Boards are declared by name as
  `HOST[:PORT]`. Names follow `.lxf` where they map (`strip`, `instances`,
  `tags`) [S309]; nested fixtures, `arc`, `points` and transform chains
  stay Phase 3.
- **Plan orientation.** The file is a plan: x to the right, y up the page,
  an optional third coordinate z for height, right-handed. This is the 2D
  view the preview and patterns already use (`grid` is in the xy plane);
  it differs from `.lxf`'s y-up 3D convention [S309], which the Phase 3
  format keeps.
- **Pitch.** The default pitch is length / pixels, and the pixels are
  centred on the strip, so the end pixels sit half a pitch in from each
  end: a 64-pixel bar 1 m long has a 1/64 m pitch. A 1 m strip of 60 LEDs
  is sold as 60 LEDs per meter [S761], and cut pads sit between LEDs, each
  LED inside its own pitch-long segment [S762]. That an LED is centred in
  its segment is an inference. A measured `pitch` overrides the default
  (spacing shifts 2–3 mm at a strip's half-meter joins [S762]); the pixels
  stay centred on the strip.
- **Normalization: Contain, centred.** One scale, 1 / the longest extent of
  the pixel centres, for every axis, so a wave crossing the room keeps its
  shape; Fill stretches each axis [S202]. Each shorter axis is centred in
  0–1, so (0.5, 0.5) is the middle of the room; an axis with no extent is 0,
  as in `line` and `grid`. The compiled map records each axis's span. The
  raw meters are kept beside the normalized mapping (this ADR's
  "raw physical coords").
- **Wire order and board ranges.** Board (in declaration order), then
  output, then chain position; a fixture's pixel 0 is at its input end.
  Each board takes one contiguous range of the map, the form the DDP sink
  takes (ADR-003), with its outputs back to back inside it. `--dry-run`
  prints each output's start and length for the board's LED settings.
- **Wiring checks at load**, after xLights' model chains and its controller
  visualizer, which refuses an upload with errors [S1278][S1279]: pixels
  per output against WLED's 2,048 (`MAX_LEDS_PER_BUS`) and per board
  against 16,384 (`MAX_LEDS`), both in `wled00/const.h` at v16.0.1
  [S1250]; chain positions per output must run 1..k with no gap or
  duplicate; two board names for one host:port are overlapping ranges on
  one device (LedFx warns on overlapping segments [S305]); every fixture
  must name its input end. Unknown keys, undeclared or unused boards and
  duplicate ids also fail. All problems are reported together, each naming
  its fixture or board and never a path.
- **Live reload.** A save recompiles the file on the loop thread. The new
  map is applied only if it compiles, the DDP sink accepts its boards, and
  the pattern's `setup` accepts the new geometry; otherwise the last good
  map keeps running and the status line says why. Engine time continues;
  buffers re-zero, as on any rebind (ADR-005 amendment 2026-07-27).
- **Fixture units: render at fixture centres, then gather.** A pattern
  lights a whole fixture as one unit by rendering once per fixture at the
  fixture's centre; the engine gathers that F-colour frame out to the
  N pixels with one index table (pixel → fixture). The pattern sees n = F
  and `index` = the fixture's wire-order position, and sinks and the
  preview still see every pixel at its real position. Precedents: xLights
  "Single Line as a Pixel" [S1278], LedFx grouping [S305], WLED segment
  grouping [S1262].
- **Who selects: the pattern, with a run-time override.** A class
  attribute, `units = "fixture"` (default `"pixel"`), states what the
  pattern was written for; `run --units pixel|fixture` overrides it for
  every pattern in the run. A mapping without fixtures renders per pixel
  either way, bit-identical to before. A hot reload that changes `units`
  rebinds the new pattern to the other geometry.
  *(Superseded 2026-11-07: with the bullet above, every layer renders per pixel; see ADR-025.)*
- **ADR-005 is unchanged.** `render(x, y, z, index)` keeps its signature
  and meaning (one element per thing rendered); `units` is an optional
  class attribute, so no ADR-005 amendment is needed.
- **Floor plan: an optional `plan` key, two-point calibration.** `{"image",
  "points", "meters", "at"}`: an image file relative to the room file, two
  image pixels `meters` apart (xLights' ruler sets real length from two
  points [S1279]), and `at`, the room meters of the first point (default
  [0, 0]). The image is not rotated: its x is the room's x and its y runs
  down the page. Calibration is checked at load (two distinct points, a
  positive distance, a .png/.jpg/.jpeg/.webp/.gif name); whether the file
  exists is not, so a missing image never stops the aura. The preview
  serves the image from the laptop at a fixed URL, so no path reaches the
  socket, and dims it from the page (xLights' background brightness
  [S1278]).
- **True-to-life preview.** The page sizes each dot from its fixture's
  pitch in meters times the room's meters-to-screen scale, and draws the
  dots additively, so overlapping glow sums as light does. Precedents:
  xLights' pixel size and blended circles [S1278], Chromatik's point size
  and blend [S1277], FastLED ScreenMap's physical dot diameter [S1280].

### Consequences

- The laptop simulation and the board split come from one file, and the
  file can change during setup without a restart.
- Every gallery pattern runs per bar with `--units fixture`; a canopy-set
  pattern declares the unit it was written for in one line.
  *(Superseded 2026-11-07: there are no fixture units; see ADR-025.)*
- A per-fixture pattern's buffers are per fixture (`self.pixels` is
  (F,3)); a change of units starts them fresh.
- The DDP sink and the preview gained a relayout path (`DdpSink.prepare`/
  `commit`, `PreviewSink.remap` and a `layout` message). A frame rendered
  just before a relayout is dropped, not sent to the wrong ranges.
- The ANSI sink cannot draw a room and is refused with `--room`. The
  preview page now fits a 2D map's bounding box, which leaves 0–1 maps
  unchanged; the ANSI half of "Normalize preview layouts per axis"
  (`docs/backlog/unscheduled.md`) is still open.
- The compiled map keeps its meters-to-normalized transform (`scale`,
  `shift`), so the plan image and the fixtures share one coordinate frame
  on the page.
- A plan drawn at the wrong angle needs the image rotated before use; a
  rotation key is left out until a real plan needs one (inference: room
  floor plans are usually drawn square to the walls).

### Evidence

- [S309] Chromatik `.lxf`: `strip` with `numPoints`/`spacing`, `instances`
  for arrays, `tags`, per-component outputs — the shape and names reused.
- [S202] Pixelblaze mapper: one map of physical units normalized to 0–1
  world units; Fill versus Contain.
- [S761] A 1 m strip of 60 LEDs is "60 LEDs-per-meter": pitch is length /
  count, the 1/64 vs 1/63 answer.
- [S762] Cut pads between LEDs; spacing changes at half-meter joins —
  the half-pitch inset (inference) and the `pitch` override.
- [S1278][S1279] xLights: model chains, overlap checks, a visualizer that
  refuses upload on errors — the wiring checks' precedent.
- [S1250] WLED v16.0.1 `wled00/const.h`: `MAX_LEDS_PER_BUS` 2048,
  `MAX_LEDS` 16384 on ESP32/S3 — the limits checked.
- [S1278][S305][S1262] One colour per prop while the preview shows every
  pixel (xLights "Single Line as a Pixel"), LedFx grouping, WLED segment
  grouping — three independent precedents for fixture units.
- [S1279][S1278] xLights' two-point ruler and background brightness —
  the plan calibration and its dimmer.
- [S1278][S1277][S1280] xLights' pixel size and blended circles,
  Chromatik's point size and blend, FastLED ScreenMap's dot diameter —
  physically sized, blended preview dots.

### Rejected alternatives

- **Pixels at both ends of the strip** (`linspace(start, end, n)`, the
  `line()` convention): a 1/63 m pitch on a 64-pixel, 1 m bar, which
  contradicts per-meter density [S761][S762] and puts adjacent bars'
  end pixels one pitch too close.
- **Fill normalization**: stretches each axis to 0–1 and warps any shape
  that crosses the room [S202].
- **Contain anchored at 0** (each axis from 0): leaves (0.5, 0.5) off the
  room's middle on the short axis, so centred patterns sit off-centre
  (inference).
- **A fixture argument in `render`** (`render(x, y, z, index, fixture)`):
  an ADR-005 contract change every pattern and test would carry, for a
  need one gather covers. LedFx and xLights group outside the effect
  [S305][S1278].
- **Pattern-side grouping** (hand the pattern the pixel → fixture table
  and let it index): every per-bar pattern would repeat the same gather,
  and its per-fixture state would be N-sized.
- **WLED segment grouping on the board** [S1262]: a board-side effect
  setting, not a property of the frame pewpew streams, so neither the
  simulation nor the gallery patterns would see it (inference).
- **A plan placed by two image points and two room points** (a similarity
  transform with rotation): one more pair of numbers to measure on build
  day, for a rotation no plan in hand needs (inference); the xLights ruler
  takes one known length [S1279].
- **Dots sized to fill a square** (the page's earlier formula): on the
  3,840-px canopy each dot was several pitches wide, so bars blurred into
  bands and the simulation could not judge pixel spacing.
- **A run option only, or a class attribute only**: a class attribute
  alone needs a subclass to run a gallery pattern per bar; an option alone
  leaves a per-bar canopy-set pattern's intent outside its file.

## Amendment (2026-11-07) — One rig description

The room map (amendment 2026-10-30) and the arrangement (amendment
2026-10-22) described the same rig twice, with two compilers, two Contain
rules and two copies of the WLED caps. The arrangement becomes the one rig
format. It takes over what only the room map had, and the room map is
retired through a migration. Code: `src/pewpew/rig/`, `src/pewpew/mapping.py`,
`src/pewpew/floorplan.py`.

### Decision

- **D1 Render frame.** Arrangement files stay y-up (amendment 2026-10-22).
  Looks see the plan frame of the room map, `line` and `grid`: x right, y up
  the plan, z height. The compiled mapping is `contain(positions_m @ C^T)`,
  with C the MVR conversion above. `positions_m` and the matrices stay y-up
  for 3D.
- **D2 Contain rule.** One `contain` for every map, the room map's: one scale
  for every axis, shorter axes centred, and a flat axis or a single point at
  0 [S202]. Room mappings stay bit-identical.
- **D3 Parametric strip.** A catalog fixture type `strip` with dims
  `pixels`, `length` and `pitch`, where the pixel span is `pixels * pitch`
  and `pitch` defaults to `length / pixels`. This is the room map's pitch
  rule [S761][S762], and the parameters of Chromatik's Strip (Points,
  Spacing) [S317][S309] and xLights' Single Line (nodes per string)
  [S318]. A fixture or a group may give `dims` overrides. Compile turns each
  distinct set into a variant type `<type>.<sha8>`, the first 8 hex digits
  of the SHA-256 of the canonical JSON of the overrides, in a catalog
  overlay that the catalog checks as it checks a loaded entity. The
  catalog digest stays the loaded catalog's. A pixel count may be an
  expression; it must give a whole number from 1 to 4,096
  (`MAX_FIXTURE_PIXELS`, so a dims override cannot make the compiler
  allocate without limit). The pixels must fit between the `end_a` and
  `end_b` anchors. The strip uses a new generic `ws2812b` chipset; its
  power is marked assumed.
- **D4 Controller address.** `controllers[].host` is `HOST[:PORT]`, checked
  as the room map checks a board. The address sits beside the device's
  placement in the scene, as MVR keeps a fixture's network address with it
  [S319][S316]. Two controllers on one host:port is the compile error
  `address_used_twice`: their ranges would overlap on one device. xLights
  allows two outputs on one IP but calls it "highly not recommended"
  [S164]; the room map already refused it. Room map and arrangement call
  one check (`pewpew.sinks.ddp.shared_targets`).
- **D5 Input end.** No new field. A fixture's pixel 0 is at local −y, so the
  room map's `input` end becomes the direction of `aim.axis`, from the
  input end to the far end. xLights sets a line's direction by the end its
  wiring starts from [S318]. Rings keep `data_in`.
- **D6 Caps.** The catalog's firmware entry is the one source of the pixels
  per output and per controller [S1250]. The room map reads the same
  figures from it. As in xLights, the caps live in the controller
  definition, not in code [S1279]. A run will refuse to stream over a cap
  once the runtime reads arrangements.
- **D7 Room map deprecation.** For one release, `--room` is an alias of
  `--map`, and a room file is migrated in memory with a warning that names
  `pewpew rig migrate-room`. The release after that refuses it. Rebinding is
  refused on a legacy room file. This follows PEP 387's order (warn, wait,
  then remove, naming the release) [S783] with a shorter wait.
- **D8 Version.** The arrangement stays at format v1. Its new fields are
  optional and additive: `notes`, `plan`, `controllers[].host`, and `tags`
  and `dims` on fixtures and groups. A file without them reads as before.
  A reader older than a field refuses it as unknown, the precedent of the
  `power` block. `plan` is the room map's two-point calibration
  (`pewpew.floorplan`, one checker for both formats), in plan-frame meters.
  The compiled rig also carries `controllers` (id, profile, host, port),
  `scale`, `shift` (mapping = plan meters × scale + shift), `plan` and
  `variants`.

### Consequences

- The runtime, the preview and the studio can work from one compiled rig.
  The room compiler is deleted once the runtime reads arrangements and
  `rig migrate-room` proves the migrated mapping, ids, ranges and DDP
  targets equal the room's.
- A strip variant is a fixture type with no file of its own. Anything keyed
  by type id, such as a prebuilt 3D assembly, has to build or fall back for
  `<type>.<sha8>` ids (inference).
- Room map files keep compiling unchanged through the deprecation window,
  and their WLED caps now follow the catalog.

### Evidence

- [S317][S309] Chromatik's Strip is set by Points and Spacing — a strip
  given by count and pitch.
- [S318] xLights' Single Line is set by nodes per string, with its direction
  from the end its wiring starts at — the parametric strip and D5.
- [S761][S762] Pitch is length / count, with LEDs inside pitch-long
  segments — the default pitch.
- [S319][S316] MVR keeps a fixture's network address (IPv4 or hostname) with
  the fixture in the scene — `controllers[].host`.
- [S164] xLights treats two outputs on one IP as an unmanaged, not
  recommended setup — the precedent for checking it, here made an error.
- [S1250][S1279] WLED's caps in `wled00/const.h`, and xLights' per-controller
  caps in its controller definition files — one data source for caps.
- [S783] PEP 387: warn, wait, then remove — the deprecation window.
- [S202] Contain keeps one scale for every axis — D2.

### Rejected alternatives

- **Keep both formats.** Two compilers, two Contain rules and two copies of
  the caps had already drifted apart: the rig's Contain put a flat axis at
  0.5, the room's at 0 (inference).
- **The rig's Contain rule (a flat axis at 0.5).** It would change every
  room mapping and break the migration's equality proof (inference); D2 is
  the room's rule [S202].
- **A line fixture outside the catalog** (the room map's `start`/`end`
  strip in the arrangement). It would bypass the chipset, power and 3D
  parts that every catalog type has. Chromatik and xLights both make a
  strip one fixture kind among others [S317][S318].
- **An `input` field on fixtures.** It would be a second way to set the
  direction that `aim` already sets (inference).
- **Board hosts only on the command line.** The room map already kept them
  in the file, and MVR keeps addresses in the scene [S319].
- **Caps as constants in code.** That was the second copy this amendment
  removes; the WLED caps change with the firmware version [S1250], and
  xLights keeps them in data [S1279].
- **An arrangement v2 with a migration step.** Every new field is optional,
  so v1 readers lose nothing they could read, and a v2 would make every v1
  file go through a migration for no change in meaning (inference).
- **Removing `--room` at once, or PEP 387's two-release wait.** Removing it
  at once breaks a working setup without warning [S783]. A two-release wait
  keeps two compilers alive for longer than a 0.0.x project needs
  (inference).

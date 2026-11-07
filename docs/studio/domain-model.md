# A6. Domain model design (Plan agent, Opus, 2026-10-22; revised with full links)

Brief: design the composable rig model (catalog, arrangement, wiring and power) under the constraints
in this plan, with an accurate bar assembly, INV-002 expressible as data alone, and every source
cited as a full link. This is the revised final message. Step 0 saves it as
`docs/studio/domain-model.md`.

# pewpew rig model: design (2026-10-22)

**How to read the citations.**
- A local citation such as `docs/studio/prototype/golden-tubes-3d.html:320` gives the file and the line. **Sources** lists every file and every line cited.
- Web and GitHub sources are linked inline with full URLs. GitHub links are pinned to a tag or commit.
- In catalog JSON, `src` holds a record ID (`RES-`, `Q-`, `INV-`, `PRT-`) from the maintainer's fixture notes, a vendor drawing or datasheet, or a URL. The notes and the copies of the vendor drawings and datasheets are not public.
- "(inf)" marks an inference. "(summary, no link)" marks a figure from the coordinator's research summary that I could not find a link for.

## 1. Layers and entities

The model has three layers. The split between product data and placement follows GDTF and MVR. The electrical objects are my own design. GDTF's `WiringObject` has ComponentType Input, Output, PowerSource, Consumer and Fuse, plus FuseCurrent, but nothing for cable length or gauge ([gdtf-spec.md L1612-L1646](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md#L1612-L1646)).

**Conventions.**
- Values are SI floats with unit suffixes (`_m`, `_w`, `_a`, `_v`, `_s`, `_deg`, `_mm2`).
- Any catalog fact is either a literal or `{"v","status","src"}`. Status is one of `measured | stated | inferred | derived | assumed`; anything other than `measured` counts as unmeasured.
- A numeric field may be an expression over the entity's `dims`, using only `+ - * / ()`. One restricted `ast` evaluator on the server handles these; the browser never evaluates them.

**Catalog** (hand-written data shipped in the package, one JSON file per entity, discriminated by `kind`):

| kind | fields |
|---|---|
| `fixture_type` | `dims`; `profiles` (2D CSG built from `rect`, `circle`, `polygon`, `ref`, `minus`); `parts` [{profile or box, `range_m`, `taper_to`, `glow`, `gain`, `finish`}]; `anchors` {at, dir, connector, gender, pigtail_m, accepts}; `pixels` {count, span_m, z_m, leds_per_pixel, facing, beam_deg, chipset, channels, color_order}; `power` {v_nominal, max_w, measured_w, passthrough_ohm} |
| `attachment_type` | fits (a host profile name), dims, parts (which may use `host:<profile>`), anchors |
| `chipset` | bit_s, reset_s, bits_per_channel |
| `connector` | pins, rated_a, pinmap |
| `cable` | length_m (or per metre), ends, conductors_mm2 {vplus, gnd, data, spare} |
| `psu` | v_out, i_max_a |
| `firmware` | per-output and total pixel caps, warning threshold, min frame interval, ingest, `led_types` table mapping (chipset, channels) to a firmware type |
| `controller` | firmware, outputs [{id, group}], groups {same_led_type}, data_out_v, lead_max_m, network, power_w? |

Values the compiler derives from the catalog:
- Time per pixel: `t_px = bits_per_channel × len(channels) × bit_s`. That gives 40 µs for RGBW and 30 µs for RGB, matching RES-031.
- Current: `I = max_w / v_nominal`.
- Wire resistance: `R/m = ρ/A` with ρ = 1/(58×10⁶ S/m) = 1.724×10⁻⁸ Ω·m. The 58 MS/m figure is IACS copper at 20 °C ([International Annealed Copper Standard](https://en.wikipedia.org/wiki/International_Annealed_Copper_Standard)); taking the reciprocal is arithmetic. This reproduces the AWG table: 0.01724/0.823 mm² = 20.95 mΩ/m for 18 AWG, 13.17 for 16 AWG and 8.29 for 14 AWG ([American wire gauge](https://en.wikipedia.org/wiki/American_wire_gauge)).

**Arrangement** (written by the user or the studio):
- `fixtures` [{id, type, pose, attach}]
- `groups` [{id, preset `ring|array`, type, params, pose, attach}]
- `controllers` [{id, profile, position_m?}]
- `psus` [{id, type, position_m?, powers?}]: `powers` names the controllers the PSU also powers through a buck
- `wiring`, either explicit (`chains` [{controller, output, fixtures[], color_order?, tee?}], `feeds` [{psu, chain, first, count, cable, length_m, fuse_a}]) or `auto` {options}

A feed powers a contiguous run of one chain. It injects at the input of its `first` fixture, with V+ left open toward the upstream run, following RES-033's split-V+ idea (inf). A chain with `tee` hangs its fixtures on the drops of a T trunk. Each fixture takes data and power at its `in` port and sends its data back up the same drop, as Clen's fold-back tubes do on its T-cable (Clen's fold-back T-cable diagram for the 360 tube; RES-016). So a link runs from one fixture's `in` to the next one's, its path adds the fixture's return (`|out − in|`), and the trunk run, not the fixture, carries the current on, with no pass-through. That a bar returns its data this way is an inference.

Addressing sits on the wiring layer, not on the fixture type. MVR puts `Addresses` on the fixture instance ([mvr-spec.md L1005-L1007](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md#L1005-L1007)). The coordinator's wider survey says the same of port, start, count, colour order, reverse and null pixels (summary, no link).

**Derived, never stored:** instance ids such as `ring/3`, world matrices, the pixel table, output slices, auto wiring, and the report. A studio "freeze wiring" action writes the auto result back as explicit wiring.

## 2. JSON examples

**INV-001.** The drawing gives a housing of 18 × 18.5 mm, a 30.2 mm round diffuser and 45.5 mm overall (Clen's diffuser dimension drawing). That places the diffuser axis 30.4 mm above the housing base and the flat 11.9 mm below the axis. The flat's chord is then 2√(15.1² − 11.9²) = 18.6 mm, which agrees with the 18 mm housing width (arithmetic). The bare-housing beam drawing puts the LEDs on the housing's top face (Clen's beam-angle drawing, inf). The T-slot takes Clen's joiner bar (Clen's end-to-end joining drawing).
```json
{"kind":"fixture_type","id":"clen-rgbw-bar-1m","rev":1,"name":"1M LED Pixel Bar","inventory":"INV-001",
 "dims":{
  "length":{"v":1.000,"status":"stated","src":"RES-038"},
  "housing_w":{"v":0.018,"status":"stated","src":"Clen's diffuser dimension drawing"},
  "housing_h":{"v":0.0185,"status":"stated","src":"Clen's diffuser dimension drawing; the maintainer's rough figure ~0.025 (RES-011)"},
  "overall_h":{"v":0.0455,"status":"stated","src":"Clen's diffuser dimension drawing"},
  "diffuser_d":{"v":0.0302,"status":"stated","src":"Clen's diffuser dimension drawing; stated by the maintainer as 1 3/16 in"},
  "axis_z":{"v":"overall_h - diffuser_d/2","status":"derived"},
  "flat_z":{"v":"axis_z - housing_h","status":"derived"},
  "wall":{"v":0.0015,"status":"assumed","src":"Q-011"},
  "slot_open_w":{"v":0.008,"status":"assumed","src":"Clen's diffuser dimension drawing, scaled by eye"},
  "slot_w":{"v":0.013,"status":"assumed","src":"Clen's diffuser dimension drawing, scaled by eye"},
  "slot_h":{"v":0.003,"status":"assumed","src":"Clen's diffuser dimension drawing, scaled by eye"},
  "lip_t":{"v":0.0015,"status":"assumed","src":"Clen's diffuser dimension drawing, scaled by eye"},
  "cap_t":{"v":0.004,"status":"assumed","src":"not found; Q-012"},
  "pigtail":{"v":0.20,"status":"measured","src":"measured by the maintainer: about 20 cm long"}, "pigtail_inset":{"v":0.15,"status":"measured","src":"measured by the maintainer: each pigtail leaves the underside 15 cm in from its end, at right angles to the bar"},
  "led_w":{"v":0.005,"status":"assumed","src":"CL05 package not found (RES-008)"}},
 "profiles":{
  "housing":{"rect":["housing_w","housing_h"],"at":[0,"housing_h/2 - axis_z"],
    "minus":[{"rect":["slot_open_w","lip_t"],"at":[0,"lip_t/2 - axis_z"]},
             {"rect":["slot_w","slot_h"],"at":[0,"lip_t + slot_h/2 - axis_z"]}]},
  "flat_cut":{"rect":["diffuser_d","diffuser_d"],"at":[0,"-flat_z - diffuser_d/2"]},
  "diffuser_outer":{"circle":"diffuser_d","minus":[{"ref":"flat_cut"}]},
  "diffuser_inner":{"circle":"diffuser_d - 2*wall","minus":[{"ref":"flat_cut"}]},
  "diffuser":{"ref":"diffuser_outer","minus":[{"ref":"diffuser_inner"}]}},
 "parts":[
  {"id":"housing","profile":"housing","range_m":["cap_t - length/2","length/2 - cap_t"],"glow":"none","finish":"black-anodized"},
  {"id":"cap_a","profile":"housing","range_m":["-length/2","cap_t - length/2"],"glow":"none","finish":"black"},
  {"id":"cap_b","profile":"housing","range_m":["length/2 - cap_t","length/2"],"glow":"none","finish":"black"},
  {"id":"strip","box":[0.010,"length",0.001],"at":[0,0,"-flat_z - 0.0005"],"glow":"none"},
  {"id":"leds","box":["led_w","led_w",0.0016],"at_pixels":true,"glow":"pixel_nearest"},
  {"id":"diffuser","profile":"diffuser","range_m":["-length/2","length/2"],"glow":"pixels","gain":1.0,"finish":"opal"}],
 "anchors":{
  "end_a":{"at":[0,"-length/2",0],"dir":[0,-1,0],"accepts":"diffuser_outer"},
  "end_b":{"at":[0,"length/2",0],"dir":[0,1,0],"accepts":"diffuser_outer"},
  "in":{"at":[0,"pigtail_inset - length/2","-axis_z"],"dir":[0,0,-1],"connector":"clen-4pin","gender":{"v":"male","status":"inferred","src":"RES-010"},"pigtail_m":"pigtail"},
  "out":{"at":[0,"length/2 - pigtail_inset","-axis_z"],"dir":[0,0,-1],"connector":"clen-4pin","gender":{"v":"female","status":"inferred","src":"RES-010"},"pigtail_m":"pigtail"},
  "tslot":{"at":[0,0,"-axis_z"],"dir":[0,0,-1],"src":"Clen's end-to-end joining drawing"}},
 "pixels":{"count":64,"span_m":"length","z_m":"-flat_z","leds_per_pixel":1,"facing":[0,0,1],
  "beam_deg":{"v":330,"status":"stated","src":"Clen's beam-angle drawing"},
  "chipset":{"v":"sk6812","status":"inferred","src":"RES-003, RES-036"},"channels":"RGBW",
  "color_order":{"v":"GRBW","status":"assumed","src":"open; tracked in the maintainer's fixture notes"}},
 "power":{"v_nominal":{"v":24,"status":"stated","src":"RES-038; lights at 5 V (RES-036); Q-004"},
  "max_w":{"v":25.6,"status":"stated","src":"RES-038"},"measured_w":null,"passthrough_ohm":null}}
```

**INV-002.** In the drawing, the 996 mm dimension of the 1 m tube spans cap to cap (Clen's 360 tube dimension drawing).
```json
{"kind":"fixture_type","id":"clen-360-tube-1500","rev":1,"name":"1.5M 360 LED Tube","inventory":"INV-002",
 "dims":{"length":{"v":1.500,"status":"stated","src":"label, recorded by the maintainer; Clen lists 1480 mm for 36 px (RES-012)"},
  "tube_d":{"v":0.040,"status":"stated","src":"label, recorded by the maintainer; RES-012"},
  "cap_d":{"v":0.042,"status":"stated","src":"RES-012; Clen's 360 tube dimension drawing"},
  "cap_t":{"v":0.020,"status":"assumed","src":"Clen's 360 tube dimension drawing, undimensioned"},
  "wall":{"v":0.002,"status":"assumed","src":"placeholder"}},
 "profiles":{"tube":{"circle":"tube_d","minus":[{"circle":"tube_d - 2*wall"}]},"cap":{"circle":"cap_d"}},
 "parts":[{"id":"tube","profile":"tube","range_m":["cap_t - length/2","length/2 - cap_t"],"glow":"pixels","gain":1.0,"finish":"opal"},
  {"id":"cap_a","profile":"cap","range_m":["-length/2","cap_t - length/2"],"glow":"none","finish":"aluminum"},
  {"id":"cap_b","profile":"cap","range_m":["length/2 - cap_t","length/2"],"glow":"none","finish":"aluminum"}],
 "anchors":{"end_a":{"at":[0,"-length/2",0],"dir":[0,-1,0]},"end_b":{"at":[0,"length/2",0],"dir":[0,1,0]},
  "in":{"at":[0,"-length/2",0],"connector":"clen-4pin","gender":{"v":"male","status":"inferred","src":"RES-016"}},
  "out":{"at":[0,"length/2",0],"connector":"clen-4pin","gender":{"v":"female","status":"inferred","src":"RES-016"}}},
 "pixels":{"count":36,"span_m":"length - 2*cap_t","z_m":0,"leds_per_pixel":6,"facing":null,"beam_deg":360,
  "chipset":{"v":"ucs1903n","status":"inferred","src":"RES-015"},"channels":"RGB",
  "color_order":{"v":"RGB","status":"stated","src":"RES-012"}},
 "power":{"v_nominal":24,"max_w":{"v":36,"status":"stated","src":"label, recorded by the maintainer"},"measured_w":null,"passthrough_ohm":null}}
```

**Firmware and controller.**
```json
{"kind":"firmware","id":"wled-16.0.1",
 "max_px_per_output":{"v":2048,"src":"https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L575"},
 "max_px_total":{"v":16384,"src":"https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L543-L551"},
 "warn_px_per_output":{"v":800,"src":"https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm#L494-L496"},
 "min_frame_interval_s":{"v":0.015,"src":"https://github.com/wled/WLED/blob/v16.0.1/wled00/udp.cpp#L477"},
 "ingest":{"protocol":"ddp","udp_port":4048,"send":"RGB","auto_white":"accurate","src":"RES-028; backlog story 'DDP 8-bit sink to stock WLED nodes'"},
 "led_types":[{"chipset":"sk6812","channels":"RGBW","type":30,"label":"SK6812/WS2814 RGBW","src":"https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L332"},
              {"chipset":"ucs1903n","channels":"RGB","type":22,"label":"WS281x RGB","src":"https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L324"}]}
{"kind":"controller","id":"esp32s3-devkitc1-ahct125","firmware":"wled-16.0.1",
 "outputs":[{"id":"rmt0","group":"rmt"},{"id":"rmt1","group":"rmt"},{"id":"rmt2","group":"rmt"},{"id":"rmt3","group":"rmt"}],
 "groups":{"rmt":{"same_led_type":false}},
 "data_out_v":{"v":3.94,"status":"stated","src":"RES-030"},
 "lead_max_m":{"v":10,"status":"inferred","src":"https://quinled.info/2021/03/10/maximum-length-data-wire-leds-ws2812b-sk6812-ws2815"},
 "network":["wifi"]}
```
**Controller notes.**
- **Output count.** The profile lists four outputs because each board has one quad 74AHCT125 (RES-031; PRT-006). The S3 builds in WLED with 4 RMT and 8 LCD-parallel channels ([const.h L86-L89](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L86-L89)). The parallel outputs share one LED type (RES-028, inf). They would come in as a data change with a `same_led_type: true` group once a second shifter is fitted. The backlog advises using the RMT outputs (backlog story "Wi-Fi ingest test on the real rig").
- **Lead length.** QuinLED's 10 m figure assumes a level shifter, a 249 Ω resistor and a separate data wire of AWG26 or thicker (https://quinled.info/2021/03/10/maximum-length-data-wire-leds-ws2812b-sk6812-ws2815). Applying it to this board is an inference.

**Arrangement** (format v1):
```json
{"format":"pewpew.arrangement","version":1,"name":"ring of 8 + tube",
 "groups":[{"id":"ring","preset":"ring","type":"clen-rgbw-bar-1m","count":8,"start_radius_m":0.618034,
  "angle_offset_deg":0,"tilt_deg":30,"roll_deg":0,"data_in":"inner",
  "attach":{"inner":"point-v0","outer":"eye-v0"},
  "pose":{"position_m":[0,0.9,0],"quat_xyzw":[0,0,0,1]}}],
 "fixtures":[{"id":"tube1","type":"clen-360-tube-1500",
  "pose":{"position_m":[0,2.0,0],"quat_xyzw":[0,0,0.7071068,0.7071068]}}],
 "controllers":[{"id":"c1","profile":"esp32s3-devkitc1-ahct125","position_m":[0,0,-1.5]}],
 "psus":[{"id":"p1","type":"meanwell-lrs-350-24"}],
 "wiring":{"target_fps":40,
  "chains":[{"id":"A","controller":"c1","output":"rmt0","fixtures":["ring/0","ring/1","ring/2","ring/3"]},
            {"id":"B","controller":"c1","output":"rmt1","fixtures":["ring/4","ring/5","ring/6","ring/7"]},
            {"id":"T","controller":"c1","output":"rmt2","fixtures":["tube1"]}],
  "feeds":[{"id":"f1","psu":"p1","chain":"A","first":0,"count":2,"cable":"wire-16awg-pair","length_m":2.0,"fuse_a":3},
           {"id":"f2","psu":"p1","chain":"A","first":2,"count":2,"cable":"wire-16awg-pair","length_m":2.0,"fuse_a":3},
           {"id":"f3","psu":"p1","chain":"B","first":0,"count":2,"cable":"wire-16awg-pair","length_m":2.0,"fuse_a":3},
           {"id":"f4","psu":"p1","chain":"B","first":2,"count":2,"cable":"wire-16awg-pair","length_m":2.0,"fuse_a":3},
           {"id":"f5","psu":"p1","chain":"T","first":0,"count":1,"cable":"wire-16awg-pair","length_m":2.0,"fuse_a":3}]}}
```
Writing `"wiring":{"auto":{"target_fps":40,"fixtures_per_output":4}}` instead derives the same chains and feeds. The PSU entry is `{"kind":"psu","id":"meanwell-lrs-350-24","v_out":24,"i_max_a":14.6}`; its 14.6 A rated current comes from Mean Well's datasheet ([LRS-350-SPEC.PDF](https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF)).

## 3. Pose and presets

**Frames.** World coordinates are metres, y-up and right-handed (research/synthesis/decisions/ADR-007-mapping-calibration.md:16-21). glTF uses the same convention: right-handed, +Y up, metres ([glTF 2.0 §3.4](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units)), with node rotation as an XYZW unit quaternion ([§ node.rotation](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#_node_rotation)).

Rotations are stored as a quaternion in xyzw order, the order three.js's `Quaternion.toJSON()` returns ([three.js Quaternion](https://threejs.org/docs/pages/Quaternion.html)). For byte-stable files the quaternion is canonicalized to w ≥ 0, and |q| must be within 1e-6 of 1 before it is renormalized. Placement is `M_world = M_group · T(p) · R(q)`. Matrices go to three.js column-major, the order `Matrix4.elements` uses ([three.js Matrix4](https://threejs.org/docs/pages/Matrix4.html)). Euler angles are never stored.

**Fixture-local frame.**
- The origin sits on the diffuser axis at mid-length.
- +Y runs from the data-in end (A) to the data-out end (B).
- +Z is the LED facing.
- X = Y × Z.

Data direction is therefore built into the geometry: local pixel j always lies at increasing y. Roll is a right-hand rotation about +Y. The prototype uses the same axes: the tube along y, x tangent to the ring, z as the face normal (docs/studio/prototype/golden-tubes-3d.html:344-345, docs/studio/prototype/golden-tubes-3d.html:424).

**Free fixtures.** As an authoring shortcut, `"aim":{"axis":[…],"roll_deg":ρ}` builds the rotation from an axis direction:
1. ŷ = the normalized axis.
2. The reference direction is world +Y, or world +Z when |ŷ·Y| > 0.999.
3. ẑ = normalize(ref − (ref·ŷ)ŷ) and x̂ = ŷ × ẑ.
4. Apply Ry(ρ).

The studio writes quaternions back.

**`ring` expansion.** For k = 0…n−1, with tilt a and roll ρ:
1. θ = offset + 360k/n.
2. Midpoint m = (r₀ + L/2)(cos θ, 0, sin θ).
3. x̂ = (−sin θ, 0, cos θ), ŷ = (cos a cos θ, sin a, cos a sin θ), ẑ = x̂ × ŷ.
4. R = [x̂ ŷ ẑ]·Ry(ρ).
5. If `data_in: "outer"`, multiply by Rz(180°), which flips the ends and keeps the facing.

This is exactly the prototype's ring loop and basis (docs/studio/prototype/golden-tubes-3d.html:380-391, docs/studio/prototype/golden-tubes-3d.html:425-430). At θ = 0 the `aim` rule gives the same basis (arithmetic). Ids are `ring/k` and order is k ascending.

**`array` preset.** `counts:[n]` or `[n,m]` with `steps_m` vectors and one member rotation, ordered row-major. This covers line and grid, and the backlog's "N bars along a wall" (backlog story "Room map file with live 2D simulation").

**MVR conversion.** MVR is right-handed, Z-up, 1 unit = 1 mm, with a 4×3 matrix in u,v,w,o rows ([mvr-spec.md L805-L823](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md#L805-L823)). To export, use `p = 1000·C·p` and `R = C·R·Cᵀ` with C = [[1,0,0],[0,0,−1],[0,1,0]]; det C = +1, so handedness holds (arithmetic). Import uses the inverse.

## 4. Compile pipeline

`compile_rig(arrangement, catalog) -> CompiledRig` takes validated models and does no I/O, reads no clock and uses no RNG.

1. **Expand** groups into instances with world matrices and attachments.
2. **Wire** the instances, from the explicit wiring or the auto rule below.
3. **Index** the pixels in data order: controllers in file order, then outputs in profile order, then chain order, then pixel j. Unwired fixtures come last and are flagged. Pixel j sits at local `(0, −span/2 + (j+0.5)·span/n, z_m)` with normal `R·facing`; omnidirectional fixtures get a zero normal. Outputs are `positions_m (N,3) f64`, `normals`, `fixture_of`, `pixel_in_fixture` and `fixture_rows (F,n_max)`. This avoids the 1/63 versus 1/64 trap the backlog warns of (backlog story "Room map file with live 2D simulation").
4. **Normalize with Contain** (backlog story "Room map file with live 2D simulation"): `(p − mid)/max(ptp) + 0.5` as float32. The result goes unchanged to `Renderer(mapping)` and `rebind` (src/pewpew/render.py:175-183). The engine already sets `index = arange(N)` (src/pewpew/render.py:197), so index follows chain order with no contract change (src/pewpew/pattern.py:6-11).
5. **Slices**: per output {start, count, led_type, color_order}, and per controller {start, count} for DDP. WLED reads the pixel format per packet and derives W from RGB (backlog story "DDP 8-bit sink to stock WLED nodes"; WLED v16.0.1 `wled00/e131.cpp:54-57` and `wled00/bus_manager.cpp:275`).
6. **Report.**

**Auto-wiring rule** (deterministic):
1. Take the fixtures in authoring order and split them into runs: consecutive members of one group (or the free fixtures) that share chipset and channels.
2. Compute the per-output fixture cap: `c_max = ⌊min(firmware cap, ⌊(1/fps − reset)/t_px⌋) / px⌋`. For the bar at 40 fps, with an 80 µs reset (the SK6812RGBW datasheet (Superlighting), p. 5), this is ⌊623/64⌋ = 9.
3. Cut each run into ⌈F/c⌉ chains with c = min(c_max, `fixtures_per_output`), sized as evenly as possible.
4. Break a chain anywhere the data path between fixtures exceeds `max_hop_m`. The path is `|out − in|×slack + pigtails`. The default of 3 m is from the summary (no link; see [this thread](https://auschristmaslighting.com/threads/maximum-distance-between-ws2811-pixel-nodes.7607)). QuinLED says LED-to-LED drive is weaker than a controller's but gives no figure (https://quinled.info/2021/03/10/maximum-length-data-wire-leds-ws2812b-sk6812-ws2815).
5. Assign chains to outputs first-fit, respecting `same_led_type` and controller totals.
6. Split each chain into feeds greedily. A feed grows while its current stays ≤ 0.75 × connector `rated_a` and its end drop stays ≤ `max_drop_fraction`.
   - The 75% loading is Littelfuse's guidance as recorded in RES-033. That row links [Fuseology Design Guide](https://info.littelfuse.com/hubfs/Fuseology%20Design%20Guide.pdf); I did not open the PDF.
   - The default `max_drop_fraction` of 0.10 is from the summary (no link; see [QuinLED's injection guide](https://quinled.info/the-ultimate-led-strip-power-injection-guide/)).
7. Pack feeds into PSUs first-fit at ≤ `psu_load_fraction`. The default of 0.8 is my placeholder, with no source ([flexfire's derating guide](https://flexfireleds.com/blog/LED-power-supply-derating) gives the same figure).

**Report contents.**
- Totals: pixels and worst-case W and A at the nominal voltage.
- Per output: pixel count, frame time, wire fps cap, LED type.
- Per data hop: path length.
- Per feed: current, fuse window `[I/0.75, rated_a]`, cable loop resistance, drop `I_seg·R_feed + Σ I_down·R_link`, and VA. The VA is set against Class 2's 100 VA only as a note, since the 100 VA figure is from the summary and I did not check it for DC (no link; see [Super Bright LEDs](https://www.superbrightleds.com/blog/is-there-a-difference-between-class-2-and-class-ii-power-supplies.html) and [EC&M](https://www.ecmweb.com/national-electrical-code/code-basics/article/20888526/classifying-and-using-c)).
- PSU load, a bill of materials, and every result that rests on an `assumed` value.

**Report for the example.**
- Pixels: 548. Chain A is 0–255, B is 256–511, T is 512–547.
- Chain A: 256 × 40 µs + 80 µs = 10.32 ms, which caps the wire at 96.9 fps. WLED shows a new streamed frame only after more than 15 ms ([udp.cpp L477](https://github.com/wled/WLED/blob/v16.0.1/wled00/udp.cpp#L477)).
- Chain T: 36 × 30 µs + 24 µs = 1.10 ms, using a reset of more than 24 µs (UCS1903N datasheet (ledco.sk), p. 5).
- Data hop `ring/k` → `ring/k+1`: 1.274 m in a straight line, 1.53 m with 1.2 slack.
- Feed f1: 2.133 A. The fuse window is 2.84–4.0 A, flagged because `rated_a` is assumed from M12's 4 A (RES-017, RES-033). A 3 A fuse fits.
- Drop at f1: 0.0527 Ω × 2.133 A + 0.0528 Ω × 1.067 A = 0.169 V (0.70%). This excludes the unmeasured bar pass-through.
- PSU p1: 10.03 A of 14.6 A (69%).
- Total: 240.8 W.

## 5. Glow on non-emitting parts

Every part declares how it glows:
- `pixels`: emissive colour is sampled along the fixture axis with linear filtering, clamped to the ends.
- `pixel_nearest`: used for the LED bodies; each takes its own pixel's colour.
- `none`: dark parts such as the housing, caps and strip.

**Sampling.** The shader sets `u = (y − y₀)/span` into a texture row that is n texels wide. Texel centres sit at (i+0.5)/n, the same convention as pixel placement. Clamp-to-edge gives any point past the lit span the end LED's colour, which is the prototype's clamp (docs/studio/prototype/golden-tubes-3d.html:320, docs/studio/prototype/golden-tubes-3d.html:328) done on the GPU.

**Attachments.** These are meshed in host coordinates, so they fall past the span and take the end LED's colour. Their shape uses the host's own outer profile, so they fit flush, as the maintainer described. They pop on and off, and the maintainer expects only faint glow through them.
```json
{"kind":"attachment_type","id":"point-v0","fits":"diffuser_outer",
 "dims":{"len":{"v":0.10,"status":"assumed","src":"prototype placeholder, docs/studio/prototype/golden-tubes-3d.html:291"},"plug":{"v":0.015,"status":"assumed","src":"Q-012"}},
 "parts":[{"id":"cone","profile":"host:diffuser_outer","range_m":[0,"len"],"taper_to":0,"glow":"pixels",
   "gain":{"v":0.25,"status":"assumed","src":"the maintainer expects only faint glow"}},
  {"id":"plug","profile":"host:diffuser_inner","range_m":["-plug",0],"glow":"pixels","gain":0.25}],
 "anchors":{"tip":{"at":[0,"len",0]}}}
```
`taper_to: 0` maps to manifold3d's `extrude(..., scale_top=(0,0))`, which gives a cone with its apex on the diffuser axis ([manifold3d.cpp L453-L462](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/manifold3d.cpp#L453-L462)). The eye is the same collar plus an `xy`-plane blade with a slot cut through it, following docs/studio/prototype/golden-tubes-3d.html:354-378.

**How the browser learns what glows.** The GLB carries part `extras` {glow, gain} and a root `pixel_axis` {y0, span, count}. Each frame, the browser fills one RGB u8 DataTexture by reading `frame[rows[f,j]]`. It uses the frames the preview protocol already sends display-ready (src/pewpew/sinks/preview.py:8-29; `to_display_u8` at src/pewpew/sinks/base.py:82-91, gamma 2.2 at src/pewpew/sinks/base.py:37). The studio raises the preview's pixel cap so nothing is decimated (src/pewpew/sinks/preview.py:31-34).

**Why the server emits GLB instead of the browser extruding profiles.**
- There is one geometry implementation. The cut-outs, the cone apex and the eye slot would otherwise need a JS copy, and pewpew retired its JS mirrors because they drifted (backlog story "Keep preview ports honest", `docs/backlog/v0.2.x.md`).
- glTF's frame matches ADR-007's and three.js's, so nothing converts.
- Deterministic bytes allow content-hash URLs that cache forever.
- L1 can test the same bytes the browser draws.

The browser composes server matrices, fills the texture and shades. It never expands presets, places pixels, wires, or does power arithmetic.

## 6. Modules, libraries, schema, versioning, validation

```
src/pewpew/rig/  __init__.py (load_arrangement, compile_rig) · models.py (pydantic; Sourced, Dim, kind union, Arrangement)
  expr.py · catalog.py (load, digest) · data/<kind>/*.json · pose.py (xyzw, aim, matrix→quat, MVR)
  presets.py · wiring.py · electrical.py · compile.py · migrate.py · geometry.py [studio extra: manifold3d→GLB]
src/pewpew/studio/ [extra] FastAPI: /api/catalog, /api/compile, /api/assembly/{digest}.glb, /api/arrangements, /ws/session
schemas/arrangement.v1.json, catalog.v1.json (generated, committed)
```

**Changes to existing code.**
- `__main__._mapping` (src/pewpew/__main__.py:62-74) accepts `*.json`.
- The map file is watched and reloaded through `Renderer.rebind`.
- The preview gets a message that resends positions; today positions go out only in `hello` (src/pewpew/sinks/preview.py:148-154, backlog story "Room map file with live 2D simulation").
- ADR-007 gets the amendment the backlog calls for (backlog story "Room map file with live 2D simulation").

**Libraries.**
- pydantic 2 in core. One of the maintainer's other fly.io apps pins `>=2.13.5`. pewpew uses no pydantic today: `ast-grep run -p 'from pydantic import $$$X' -l python src/pewpew` and grep both find nothing, while the control pattern `import $X` matches 51 lines.
- Core dependencies today are only numpy, watchfiles and websockets (pyproject.toml:6-10), with Python ≥3.11 (pyproject.toml:5). Quaternions are written in NumPy, so no new dependency.
- `manifold3d` 3.5.4 (Apache-2.0, cp311 wheels; [PyPI](https://pypi.org/project/manifold3d/)), with `Manifold.extrude` and `to_mesh` ([extrude.py L1-L19](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/examples/extrude.py#L1-L19), [manifold3d.cpp L339](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/manifold3d.cpp#L339)). A hand-written GLB writer keeps the bytes deterministic.
- FastAPI plus orval for TypeScript types, the same path the maintainer's other fly.io apps use.
- React 19, zustand 5, Vite 8 and Tailwind 4 match three of the maintainer's other web apps.
- None of the maintainer's other projects uses three.js or R3F, so that part of the stack is new. three r186 is the current release ([GitHub release](https://github.com/mrdoob/three.js/releases/tag/r186), published 2026-09-24 per [the API](https://api.github.com/repos/mrdoob/three.js/releases/tags/r186)).
- Hosting: three of the maintainer's other apps already deploy to fly.io with a `fly.toml` (FLY-*). Share links are content-addressed arrangements kept on a volume.

**Versioning.** Files carry `format` plus an integer `version`. Loading runs `migrate.py`'s pure `vN→vN+1` dict functions in order, and saving always writes the latest version. A file newer than the code is refused. The compile output includes `catalog_digest`, so a shared link can say when dimensions have changed since it was shared.

**Validation rules.**
- **Errors:**
  - unknown fields (`extra=forbid`), unresolved refs, duplicate ids
  - bad quaternion, or both `quat` and `aim` given
  - attachment `fits` does not match the anchor's `accepts`
  - a fixture in two chains, or an output used twice
  - mixed chipset or channels in one chain, or a missing `led_type`
  - expression cycles
- **Violations** (shown red; nonzero exit with `--strict`):
  - over the firmware per-output or total cap
  - a mixed `same_led_type` group
  - feed current above 0.75 × rating, or a fuse outside its window
  - PSU overload
- **Warnings:**
  - over 800 px on an output, the threshold where WLED itself warns ([settings_leds.htm L494-L496](https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm#L494-L496))
  - wire fps below target
  - drop or hop over its default
  - lead longer than `lead_max_m`
  - flat chord more than 1 mm from `housing_w`
  - results that rest on assumed values

## 7. Extension points (catalog data only)

```diff
# INV-002: no .py changes
+ rig/data/fixture_type/clen-360-tube-1500.json      (section 2)
+ rig/data/chipset/ucs1903n.json  {"kind":"chipset","id":"ucs1903n","bit_s":1.25e-6,"bits_per_channel":8,
+     "reset_s":{"v":2.4e-5,"status":"stated","src":"UCS1903N datasheet (ledco.sk) p.5 (>24 µs)"}}
  rig/data/firmware/wled-16.0.1.json  led_types:
+   {"chipset":"ucs1903n","channels":"RGB","type":22,"label":"WS281x RGB"}
```
```diff
# New controller
+ rig/data/controller/quinled-dig-octa-32-8l.json {"kind":"controller","id":"quinled-dig-octa-32-8l","firmware":"wled-16.0.1",
+   "outputs":[{"id":"o1","group":"rmt"}, … ,{"id":"o8","group":"rmt"}],"data_out_v":5.12,
+   "max_px_advised":2000,"network":["ethernet","wifi"],
+   "src":"https://quinled.info/quinled-dig-octa-brainboard-32-8l-specifications/"}
```
The Dig-Octa page lists an ESP32-WROOM-32UE, 8 level-shifted RMT outputs at 5.12 V, LAN8720A Ethernet and about 2,000 LEDs advised for WLED. Classic ESP32 builds of WLED have 8 RMT channels ([const.h L92-L93](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L92-L93)).
```diff
# New chipset (if the bench shows the tubes run at 400 kbps; RES-015, RES-029)
+ rig/data/chipset/ucs1903-400k.json {"kind":"chipset","id":"ucs1903-400k","bit_s":2.5e-6,"bits_per_channel":8,
+     "reset_s":{"v":2.4e-5,"status":"stated","src":"UCS1903 datasheet (Superlighting) p.3"}}
+ firmware led_types: {"chipset":"ucs1903-400k","channels":"RGB","type":24,"label":"400kHz RGB",
+     "src":"https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L326"}
- tube "chipset":{"v":"ucs1903n",…}   + "chipset":{"v":"ucs1903-400k","status":"measured","src":"bench <date>"}
```
The 2.5 µs bit time is 1/400 kbps (arithmetic); the low-speed mode is on p. 1-2 of the UCS1903 datasheet (Superlighting).

## 8. Tests (L1, under 30 s, all pure)

1. **Golden rings.** Two rings of 24 with r₀ = 0.618034 and 1.0, offsets 0° and 7.5°, tilt 30° (docs/studio/prototype/golden-tubes-3d.html:289-297):
   - pivots at 1.118 and 1.5 m
   - inner ring spans 0.685–1.551 m in plan
   - axis-anchor width 3.866 m ±0.5 mm (docs/studio/prototype/golden-tubes-3d.html:273, docs/studio/prototype/golden-tubes-3d.html:431-441), and 4.039 m with 0.10 m attachments (docs/studio/prototype/golden-tubes-3d.html:291)
   - band height 0.50 m, or 0.60 m with attachments
2. **Basis parity.** Each ring member's R equals the prototype's (side, dir, face) to 1e-12 (docs/studio/prototype/golden-tubes-3d.html:425-430). Quaternion → matrix round-trips, with w ≥ 0.
3. **Pitch.** Pixel i is at −0.5 + (i+0.5)/64, and the pitch is exactly 0.015625 (backlog story "Room map file with live 2D simulation"). `data_in: outer` reverses world order.
4. **Contain.** The longest axis spans exactly [0,1], the other axes centre on 0.5, and aspect ratios are preserved.
5. **INV-002 is data-only.** Compiling one tube gives 36 px, 3 B/px, 30 µs/px and 1.5 A. A guard test finds no catalog id in any `rig/*.py`.
6. **Timing.** `max_px(40e-6, 80e-6, 40) == 623`. A 10-bar chain runs at 38.9 fps. A 6-tube chain takes 216 × 30 µs + 24 µs = 6.50 ms.
7. **Feeds.** On 4 A at 75%: 2 bars fit (2.133 A), 3 bars fail (3.2 A), and 2 tubes fit at exactly 3.0 A (inclusive); compare RES-033.
8. **Drop and PSU.** The §4 numbers: 0.169 V and 10.03 A.
9. **Auto wiring.** Golden rings at `fixtures_per_output: 4` give 12 chains on 3 boards. With the default cap they give six chains of 8.
10. **Determinism and schema.** Compiling twice gives identical arrays, and building a GLB twice gives identical bytes. The committed schema matches the generated one. A v1 file passes migration.
11. **Geometry** (studio extra). The bar's GLB bounds are x ±15.1 mm (the 30.2 mm diffuser),
    with the housing and caps alone at x ±9 mm, and z from −30.4 to +15.1 mm. Corrected
    2026-10-22: the first version gave x ±9 mm for the whole bar, which is only the housing; ws1b
    caught the error (`docs/studio/reports/ws1b-geometry.md`).

## 9. Open questions

1. **Bar cross-section (Q-011).** Housing depth (18.5 or about 25 mm), diffuser OD and wall, the flat's width and height, and the T-slot opening, cavity and lip. Settled by calipers (PRT-002) and a square-on photo of an end with a scale in frame.
2. **Bar ends (Q-012).** End-cap thickness and how far the diffuser extends past the strip. Settled by calipers.
3. **Pixel lattice.** The distance from the housing end to the centres of LED 1 and LED 64. This confirms the 1000 mm span and the (i+0.5)/n rule.
4. **Data order (Q-017; Q-005).** Light pixel 0, then pixel 32, alone in WLED, and confirm that male is the input. A continuity pin map would also fix the cable conductor roles.
5. **Electrical (Q-004; Q-010).** Watts at 24 V on full white and on each channel alone, and the V+ drop from the male to the female pin at 2 A, all on the bench supply (PRT-001). These fill `measured_w` and `passthrough_ohm`.
6. **Tube.** Is it 800 or 400 kbps (try WLED type 22, then 24)? Is the colour order RGB? Is it 1480 or 1500 mm long, and how long are its caps?
7. **The maintainer's decisions.**
   - Which connector rating to design to: assume M12's 4 A, or re-terminate to xConnect (Q-007).
   - Whether to fuse at the connector's rating.
   - The values for `psu_load_fraction`, `max_drop_fraction` and `max_hop_m`.
   - Whether the point and eye cover the housing ends, and their real lengths. The prototype's 10 cm is a placeholder.
   - How the bars mount, via the T-slot anchor (Q-014).
   - Whether a whole bar can light as one unit (backlog story "Room map file with live 2D simulation").

## Sources

**Local files** (repo-relative paths, with the lines cited):
- The maintainer's fixture notes (not public): the INV-, PRT-, RES- and Q- records cited above, and the maintainer's statements on the bar's depth, the diffuser's diameter, the tube's label, and the point and eye.
- `docs/studio/prototype/golden-tubes-3d.html`. Lines 263-275, 289-297, 320, 328, 344-345, 354-378, 380-391, 422-442. Screenshot: `docs/studio/prototype/overview.png`.
- `docs/backlog/v0.2.x.md`: the patch table and the stories "DDP 8-bit sink to stock WLED nodes" and "Keep preview ports honest". Also the backlog stories "Room map file with live 2D simulation" and "Wi-Fi ingest test on the real rig".
- `research/synthesis/decisions/ADR-007-mapping-calibration.md`. Lines 16-28.
- `research/synthesis/architecture.md`. Lines 76 and 301-346.
- `research/synthesis/requirements.md`. Lines 28 (Q-8) and 60 (R-1).
- pewpew source:
  - `src/pewpew/render.py`: 175-183, 185-207, 197
  - `src/pewpew/pattern.py`: 6-11
  - `src/pewpew/sinks/base.py`: 37, 82-91
  - `src/pewpew/sinks/preview.py`: 8-34, 148-154
  - `src/pewpew/__main__.py`: 62-74
  - `src/pewpew/mapping.py`: 1-9
- `pyproject.toml`. Lines 5-10.
- The maintainer's other fly.io apps (outside this repo): their `pyproject.toml`, `web/package.json` and `fly.toml`.
- Vendor drawings and datasheets, kept with the maintainer's fixture notes (not public):
  - Clen's diffuser dimension drawing
  - Clen's beam-angle drawing
  - Clen's end-to-end joining drawing
  - Clen's connection diagram for the bar
  - Clen's 360 tube dimension drawing
  - SK6812RGBW datasheet (Superlighting), p. 5 (bit time 1.25 µs ± 600 ns, Trst 80 µs)
  - UCS1903N datasheet (ledco.sk), p. 5 (reset > 24 µs), p. 4 (1.25 µs per-bit example)
  - UCS1903 datasheet (Superlighting), p. 1-2 (400/800 kbps by pin), p. 3 (reset > 24 µs)

**GitHub, pinned:**
- WLED v16.0.1 (tag commit `29b389df1c1aaec6ff53aea742d17063b985906c`):
  - [const.h L86-L89](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L86-L89)
  - [const.h L92-L93](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L92-L93)
  - [const.h L324](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L324)
  - [const.h L326](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L326)
  - [const.h L332](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L332)
  - [const.h L543-L551](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L543-L551)
  - [const.h L575](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L575)
  - [settings_leds.htm L494-L496](https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm#L494-L496)
  - [udp.cpp L477](https://github.com/wled/WLED/blob/v16.0.1/wled00/udp.cpp#L477)
  - [bus_manager.cpp L102-L125](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125) and [L275](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L275)
- GDTF and MVR spec at commit `098d3791f77f0895bd859adf01864b4826e2006f`:
  - [gdtf-spec.md L1612-L1646](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md#L1612-L1646)
  - [mvr-spec.md L805-L823](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md#L805-L823)
  - [mvr-spec.md L1005-L1007](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md#L1005-L1007)
- manifold v3.5.4:
  - [extrude.py L1-L19](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/examples/extrude.py#L1-L19)
  - [manifold3d.cpp L339](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/manifold3d.cpp#L339)
  - [manifold3d.cpp L453-L462](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/manifold3d.cpp#L453-L462)
- three.js: [r186 release](https://github.com/mrdoob/three.js/releases/tag/r186) and its [API record](https://api.github.com/repos/mrdoob/three.js/releases/tags/r186)

**Web** (read 2026-10-22):
- https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units
- https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#_node_rotation
- https://threejs.org/docs/pages/Quaternion.html
- https://threejs.org/docs/pages/Matrix4.html
- https://pypi.org/project/manifold3d/
- https://quinled.info/quinled-dig-octa-brainboard-32-8l-specifications/
- https://quinled.info/2021/03/10/maximum-length-data-wire-leds-ws2812b-sk6812-ws2815
- https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF
- https://en.wikipedia.org/wiki/American_wire_gauge
- https://en.wikipedia.org/wiki/International_Annealed_Copper_Standard
- https://info.littelfuse.com/hubfs/Fuseology%20Design%20Guide.pdf (cited through RES-033; not opened)

**Figures from the coordinator's summary with no link** (used only as labelled defaults or notes):
- the 3 m bar-to-bar data hop before a null pixel
- the 10% injection drop threshold
- Class 2's 100 VA (not checked for DC)
- the claim that formats put port, start, count, colour order, reverse and null pixels on the controller link (partly backed by MVR L1005)

**Dropped because nothing could be linked:** the 1.25× fuse rule, the date in cgworld.jp's r186 article (GitHub gives a later date), and the summary's scipy and R3F version figures.

---

**Note added by the orchestrator.** Report A3 has links for the figures this design calls
unlinked, and the step 0 link pass attaches them:

- 3 m bar-to-bar hop: https://auschristmaslighting.com/threads/maximum-distance-between-ws2811-pixel-nodes.7607
- 10% injection drop: https://quinled.info/the-ultimate-led-strip-power-injection-guide/
- Class 2 at 100 VA:
  - https://www.superbrightleds.com/blog/is-there-a-difference-between-class-2-and-class-ii-power-supplies.html
  - https://www.ecmweb.com/national-electrical-code/code-basics/article/20888526/classifying-and-using-c
- 80% PSU loading: https://flexfireleds.com/blog/LED-power-supply-derating
- 1.25× continuous-load rule (NEC 210.20(A)): https://forums.mikeholt.com/threads/80-rule-residential.115888/latest [link not verified]
- Version figures: scipy 1.18.1 needing Python 3.12 or later is at https://pypi.org/project/scipy/,
  and R3F 9.8.2 at https://registry.npmjs.org/@react-three/fiber/latest ([A5](planning/2026-10-22-a5-stack-and-libraries.md)).

The design's own "Share links ... on a volume" line is replaced by this plan's choice of Neon
(Decisions). For the texture, RGBA tagged `SRGBColorSpace` replaces "one RGB u8 DataTexture"
(Domain model section).

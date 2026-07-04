# RA-07: Mapping & topology

Last researched: 2026-07-03
Status: draft
S-ID block: S300–S349 (new IDs from S303)

## Key questions

1. What map formats exist (WLED ledmaps, xLights models, Pixelblaze pixel maps, LedFx virtuals, FPP) and what do they express?
2. What coordinate conventions are worth adopting (normalized vs world units, axis orientation, 2D/3D)?
3. Camera calibration: how does marimapper work, how accurate is it, what does GPLv3 imply? What else exists (Lightwork, ElectroMage community tools, 2024–2026 phone/AI tools)?
4. Topology beyond position: strips vs matrices vs volumes, gaps/masks, per-segment orientation, multi-controller canvases.
5. What map format + calibration path should pewpew adopt?

## Findings

### WLED ledmaps & 2D matrices

- Format: `ledmap.json` on the device filesystem — `{"map":[0,2,1,3]}`. Array **position** = logical/render order, **value** = physical LED index; zero-indexed [S303].
- Gaps: value `-1` marks a virtual/blank position, enabling non-rectangular layouts (e.g. the documented infinity-loop shape) inside a rectangular render grid [S303].
- 2D: add `"width"` and `"height"` keys beside the flattened `map` array; WLED then treats the map as a row-major matrix [S303]. If `ledmap.json` exists, any legacy `2d-gaps.json` is ignored [S303].
- Multiple maps: `ledmap1.json` … `ledmapN.json`; presets select one via `{"ledmap":N}` in the preset JSON, so a show can switch mappings at runtime [S303].
- Assessment: this is an **index-permutation** format, not a coordinate format. It expresses wiring order and rectangular-grid gaps, but carries no physical position, no units, no 3D, no per-pixel spacing. Effects remain fundamentally 1D/2D-grid; there is no notion of world coordinates. License of docs/firmware: WLED is MIT ([S001]); actively maintained (0.16 cycle, 2025–2026) [S002].
- Form factors: fine for wearables/strips and small matrices; poor fit for irregular 3D sculptures.

### Pixelblaze pixel maps

- Format: plain JSON array-of-arrays, one entry per pixel, `[x,y]` or `[x,y,z]`, in any physical unit (inches, mm, pixels) [S304]. Alternatively a JavaScript **map generator function** run in the browser editor, taking `pixelCount` and returning the coordinate array [S304].
- Normalization: "The system automatically scales pixel map coordinates to 0.0 to 1.0 values. This represents the position within the mapped world" — patterns are written in dimensionless **world units** so one pattern works on any installation [S304]. Two scaling modes: **Fill** (stretch each axis independently to 0..1) and **Contain** (preserve aspect ratio, fit largest dimension) [S304].
- Render model: with a map installed, patterns implement `render2D(index, x, y)` or `render3D(index, x, y, z)`; coordinates arrive in (0,1) world units per pixel per frame [S304][S200]. This coordinate-callback-per-pixel model is the single most influential mapping design in the hobby space and is the pattern-portability benchmark.
- Firmware is closed-source; the mapper README lives in the public simap/pixelblaze repo [S304]. Product actively maintained (v3.47 HDR drivers 2023-07; V3.66 2024-12; V3.67 2025-11) [S014][S750] (dates corrected 2026-07-03).
- Assessment: true coordinate map (2D/3D, arbitrary units, normalized at load). Gaps are simply absent pixels — every entry corresponds to a real LED, so no mask concept is needed. No explicit documented axis convention beyond x/y/z names [S304].
- Form factors: designed exactly for wearables through mid-size art; per-pixel callback costs CPU at room scale.

### xLights models / layouts

- xLights (GPL-3.0, very active — release 2026.12 on 2026-07-02 [S026]) models a display as a set of **models** (matrix, tree, arches, polyline, custom, DMX, plus submodels and groups) placed in a 2D/3D layout preview.
- **Custom models** are a grid of node numbers: the user types node/channel IDs into cells; cell position = pixel position; grid width/height adjustable, and "the depth is used to make a 3D custom model" (a stack of grids) — i.e. positions are quantized to a voxel grid, not continuous coordinates [S306]. Empty cells are implicit gaps.
- Models export as `.xmodel` XML files, which "include the faces and state definitions" for sharing/reuse [S306]; a large third-party ecosystem sells/shares `.xmodel` files for commercial props.
- Effects render into a per-model **render buffer** whose layout is chosen by *buffer style* (dynamic per model type; groups add more styles), decoupling effect space from wiring order [S307]. This buffer-style indirection is xLights's equivalent of a mapping layer.
- Assessment: sequencing-oriented; positions exist mainly to rasterize effects into per-prop buffers, not to give patterns physical coordinates. Voxel-grid custom models are clumsy for organic 3D. Room/house scale only; irrelevant to wearables.

### LedFx virtuals

- LedFx (GPL-3.0, active 2.1.x 2026 [S011]) separates **devices** (physical outputs) from **virtuals** (render canvases). Internally every device gets an implicit virtual — "it is virtuals all the way down" [S305].
- A virtual is an ordered list of **segments**: `(device, start, end, reverse)` tuples; segments from multiple devices concatenate into one 1D canvas, so one effect spans several controllers [S305]. Overlapping segments are "undefined behaviour" [S305].
- Mapping modes: **span** (one effect instance stretched proportionally across all segments) vs **copy** (effect duplicated per segment) [S305]. Extra per-virtual transforms: `rows` (reshape the 1D canvas into a 2D matrix), `grouping` (N physical LEDs act as 1 logical pixel), center offset, max brightness, transition modes [S305].
- 2D is limited: matrices are built by stacking blocks "in one dimension" only (e.g. 4×(16×64) → 64×64 works; 32×32 tiling does not) [S305]. No coordinate maps, no 3D, no arbitrary per-pixel positions.
- Newer versions precompile segment→device mappings into numpy scatter operations, "up to 13x faster frame rendering" with thousands of segments [S305] — evidence that a compiled index-gather is the right runtime representation of a map in Python.
- Assessment: virtuals are a **routing/canvas** abstraction (multi-controller canvases done well) rather than a geometry abstraction. Strongest prior art for pewpew's device/canvas split; weakest on real coordinates.

### FPP models & virtual displays

- FPP (Falcon Player, active [S022]) defines **Pixel Overlay Models** by channel arithmetic: model name, start channel, channel count, orientation, nodes-per-string, strands-per-string — mapping a linear channel range into a 2D grid [S308]. No physical coordinates; geometry is implicit in the string/strand fold description.
- Overlay states (Enabled / Transparent / TransparentRGB / Disabled) let external apps composite content over running sequences per model — a channel-range **masking/compositing** concept rather than a mapping one [S308].
- FPP also has a `VirtualDisplay` channel output that renders channel data onto a preview image using per-pixel screen coordinates — coordinates exist only for preview, not for effects [S308] (re-checked 2026-07-03: confirmed the files live under the *output* tree — `src/channeloutput/VirtualDisplay.cpp`, `VirtualDisplayBase.cpp`, `HTTPVirtualDisplay.cpp`, `HTTPVirtualDisplay3D.cpp` — i.e. a preview sink, not an effect-input coordinate model).
- Assessment: like WLED, an index/channel-space model. Confirms the pattern: player/output layers think in channels; only pattern engines (Pixelblaze, Chromatik/LX) think in coordinates.

### Coordinate conventions

Three distinct conventions coexist in the field:

1. **Index/channel space** (WLED ledmap, FPP models, LedFx segments): pixels are a permuted 1D array, optionally reshaped row-major into width×height with `-1` gaps [S303][S308][S305]. Cheap, exact for wiring, geometry-blind.
2. **Normalized world units** (Pixelblaze): author maps in any physical unit; engine rescales to 0..1 per installation, with Fill (per-axis stretch) vs Contain (aspect-preserving) policies [S304]. Patterns become installation-portable but lose true physical scale (a "10 cm ripple" is inexpressible).
3. **Physical 3D coordinates with transforms** (Chromatik/LX `.lxf`): fixtures are JSON components — `point`, `points` (explicit coord array), `strip` (count + spacing), `arc` — composed via nested fixture references and sequential translate/rotate(yaw/pitch/roll)/scale transforms; **+Y is the vertical axis**; parameters/variables (`$var`, math functions) make fixture files parametric; `outputs` bind components to Art-Net/sACN/DDP/OPC/KiNET with start/num/reverse/repeat/stride segmentation [S309]. This is the most complete declarative map format in open source; LX is by the maker of GL-heritage tools and inherits the **y-up right-handed** convention [S309].
- Precedent worth copying: Chromatik keeps *authored* coordinates physical and un-normalized, then exposes both raw (`x,y,z`) and normalized (`xn,yn,zn` in 0..1) per point to effects — patterns choose which they need [S309][NEEDS-VERIFICATION for exact field names — confirm in LX code read].
- Recommendation preview: store physical units (meters), y-up, right-handed; derive normalized coordinates at load like Pixelblaze does; keep wiring order as a separate index→coordinate table so index-space effects still work.

### Camera calibration: marimapper

- Method: lights each LED **one at a time** while a webcam records its 2D image position; the user then rotates the prop or moves the camera and rescans (ideally 3+ scans, 6–20° apart); structure-from-motion (COLMAP) reconstructs 3D positions from the multi-view 2D detections [S300]. Reconstructed LEDs are shown green; undetected LEDs are **interpolated** (shown blue) [S300].
- Output: per-scan CSV files in the working directory (2D detections), plus reconstructed 3D coordinates; 2D map available after a single scan, 3D after multiple views [S300].
- Camera requirements: any webcam with **manual exposure control** (LED blob detection needs a dark, underexposed frame); tested on HP 4310, Logitech C920, Dell integrated cams; exposure/threshold configurable; Mac exposure control is limited [S300].
- Backends: FadeCandy and FCMega tested by the author; WLED and Pixelblaze community-tested; Art-Net experimental; a documented custom-backend interface (a small Python class that turns one LED on) [S300].
- Status: GPL-3.0 (verified via GitHub API 2026-07-03); Python 3.9–3.12; active — last push 2026-03-29, ~245 stars, "major changes" branch with v4.0.0 targeted Nov 2026 [S300].
- Accuracy: no quantitative accuracy claims in the README; community reports are qualitative [S300]. Open question below.
- **GPLv3 implications for pewpew**: running marimapper as a *separate tool* and consuming its CSV/JSON output imposes nothing on pewpew — GPL governs the program's code, not its output data. Only vendoring/importing marimapper code (or linking it in-process) would pull pewpew to GPL-3.0. Ship it as an optional documented external calibration step, or write an import filter for its CSV format (formats are not copyrightable).

### Camera calibration: Lightwork and older prior art

- Lightwork (Processing/Java, GPL-3.0) mapped LEDs by webcam with two strategies: **sequential** ("fire and detect LEDs one at a time... slow for large arrays but more reliable") and **binary** ("LEDs flash a unique binary pattern, and all LEDs are mapped simultaneously. Exponentially faster for large arrays") [S301]. Output: normalized CSV consumed by its own scraper or MadMapper/TouchDesigner; controllers: PixelPusher, Fadecandy, sACN, partial Art-Net; experimental stereo 3D [S301].
- Maintenance: **dead** — last push 2019-06-28 (GitHub API, checked 2026-07-03) [S301]. Its lasting contributions are (a) the binary-code temporal multiplexing idea (log2(N) captures instead of N) and (b) normalized-CSV output as an interchange convention.
- The binary approach traces back to structured-light research; sequential per-LED remains the norm in current tools (marimapper, zranger1's mapper) because it is robust to blob-merging under diffusion [S300][S310].

### Camera calibration: ElectroMage/Pixelblaze ecosystem tools

- zranger1's "Automatic Mapping" tool (announced 2024-03-11): Python + OpenCV, webcam, one-LED-at-a-time; exploits Pixelblaze's knowledge of pixel count to retry poor detections; exports JSON/CSV or pushes the map directly to the Pixelblaze; supports map rotation and manual point editing for pixels "the vision engine can't identify" [S310]. Prototype repo: zranger1/CVTest [S310]. Practical CV gotchas recorded: auto-exposure means "you actually have to throw away the next 10 or so frames" after lighting an LED; mirrored surfaces and heavy diffusion break blob detection [S310].
- As of May 2024 the author was pivoting to an **iOS app** because a single webcam frame is too small for large installations [S310] — no evidence found of a shipped app as of 2026-07-03 [NEEDS-VERIFICATION].
- marimapper is itself cross-posted in this community with a Pixelblaze backend; the Dec 2024 forum thread shows its 3D maps driving `render3D` SDF patterns (cone + star Christmas tree) directly on Pixelblaze [S302].
- Simpler manual tools: a browser tool where you upload a photo and click each pixel to emit Pixelblaze map coordinates (forum thread 714) [S311]; the Pixelblaze editor's own map-generator JS + live 3D preview remains the baseline manual path [S304].

### Newer tools 2024–2026 (phone-based, AI-assisted)

- **LED Lab** (iOS/iPadOS, Christopher Schardt, commercial): mature phone/tablet path — camera-based ("photographically-generated") map files for odd-shaped displays, then drives the LEDs itself over Art-Net, layering on top of WLED [S312][S020]. Closed source; iOS only.
- **savdb/led_camera_map** (Python/OpenCV, MIT): blinks LEDs one at a time via Art-Net against a WLED(-MM) instance, detects blobs, and emits a WLED `ledmap.json` directly — the missing automation for WLED's manual format [S313]. Small project (~14 commits, 17 stars) [S313].
- **Vitminee/wled-mapper**: camera capture → adjustable layout → exports "both the LED map and a 2D gap mask" for WLED; self-described as "made with help of AI" — AI-assisted authorship, not AI-based detection [S314][NEEDS-VERIFICATION on activity/quality].
- No credible **AI-inference** mapper (e.g. detect-all-LEDs-from-video-with-a-neural-net) surfaced in searches as of 2026-07-03; state of the art remains sequential blink + blob detection + SfM (marimapper) [S300]. zranger1's planned iOS app (May 2024) has not visibly shipped [S310][NEEDS-VERIFICATION].
- Commercial pro tools (ENTTEC ELM with DXF-CAD import, Lightjams LED Mapper, Chromateq PIXXEM) do 2D/3D mapping from CAD drawings rather than cameras — relevant as convention prior art only [S315].

### Topology beyond position

What systems express beyond raw coordinates, and who has each concept:

- **Strips vs matrices vs volumes.** WLED: 1D segments + optional 2D matrix mode [S303]. LedFx: 1D canvas reshaped by `rows` [S305]. Pixelblaze: dimension is a property of the *map* (1D index / 2D / 3D), and the pattern picks the matching render callback — the cleanest generalization [S304]. xLights custom models add `depth` for voxel volumes [S306].
- **Gaps and masks.** WLED: `-1` entries in the ledmap [S303]. xLights: empty grid cells [S306]. FPP: overlay transparency states act as runtime masks over channel ranges [S308]. Vitminee's tool exports an explicit "2D gap mask" beside the map [S314]. Chromatik: **tags** on fixtures/components plus saved *views* (`.lxv`) select arbitrary point subsets for effects — masks as first-class named queries rather than sentinel values [S309].
- **Per-segment orientation.** LedFx segments carry a `reverse` flag [S305]; Chromatik strip outputs carry `reverse`, `stride`, `repeat` and whole fixtures carry yaw/pitch/roll transforms [S309]; WLED segments have reverse/mirror flags. Orientation belongs on the *wiring* layer (byte order out) and the *geometry* layer (transform) separately — Chromatik is the only system that cleanly splits them [S309].
- **Multi-controller canvases.** LedFx virtuals concatenate segments across devices into one canvas [S305]; Chromatik binds each fixture component to its own output (host+protocol+universe), so one world spans any number of controllers natively [S309]; xLights does the same via controller/channel assignment per model [S307]. WLED/Pixelblaze are single-controller-centric (WLED has limited multi-strip; Pixelblaze sync via Firestorm is effect-sync, not one canvas).
- **Interpolation for unmapped pixels.** marimapper interpolates LEDs the camera missed and marks them distinctly (blue vs green) [S300] — a calibration-layer concern any import path must preserve (confidence flags per point).

### Recommendation for pewpew

**Map format (cited recommendation):**
1. Adopt a **Chromatik-style declarative JSON fixture model** as the native format: components (`points` explicit array, `strip` count+spacing, `arc`), nested/parametric fixtures, sequential transforms, +Y-up right-handed, physical units (declare `"units": "m"`), and per-component output bindings — this is the proven shape that expresses strips, matrices, volumes, orientation, and multi-controller canvases in one file [S309]. Chromatik/LX is LX-licensed (source-available, restrictive for commercial use) so **copy the concepts, not the code**; the format ideas themselves are not copyrightable.
2. Present coordinates to patterns the **Pixelblaze way**: per-pixel `(index, x, y, z)` normalized 0..1 world units with Fill/Contain policy, derived at map-load time [S304] — plus raw physical coordinates for scale-aware effects. Keep index order available so 1D/index-space effects and WLED-style imports still work [S303].
3. Runtime representation: compile the map to flat numpy arrays (index→coord, coord→output-slot gather) as LedFx's complex-segments fast path proved (up to 13× faster) [S305].
4. Import filters, not format adoption, for: WLED `ledmap.json` (trivial) [S303], Pixelblaze map JSON (trivial) [S304], marimapper CSV [S300], xLights `.xmodel` (optional, for the holiday-prop ecosystem) [S306].

**Calibration path:**
- Recommend **marimapper as the external calibration tool** — actively maintained (2026), Python, sequential-blink + COLMAP SfM 3D, documented custom-backend API making a pewpew backend a ~20-line class [S300]. GPLv3 is a non-issue when invoked as a separate program whose CSV output pewpew imports; do not vendor its code.
- Provide a built-in fallback manual path (click-on-photo, à la forum tool 714 [S311]) and grid/strip generators (à la Pixelblaze map-generator JS [S304]) for the 90% case where geometry is regular.

### Verdicts

- **Pixelblaze world-unit render model** — ascendant as a *convention*; product active (firmware through V3.67, 2025-11) [S014][S304][S750]. Adopt the model.
- **Chromatik/LX .lxf fixture format** — ascendant; the most expressive open declarative map format; active [S034][S309]. Adopt the shape.
- **WLED ledmap** — stable; huge installed base, but index-only and 2D-grid-bound [S303][S002]. Import only.
- **LedFx virtuals** — stable/ascendant within Python; routing not geometry [S305][S011]. Copy the compiled-gather runtime idea.
- **xLights models / FPP models** — stable in the holiday niche; channel-space thinking, voxel-grid customs [S306][S308][S026]. Import `.xmodel` at most.
- **marimapper** — ascendant; the only actively-developed open camera 3D mapper (push 2026-03, v4 roadmap) [S300]. Recommended calibration tool.
- **Lightwork** — waning/dead (last push 2019-06-28) [S301]. Idea quarry only (binary-code capture).
- **LED Lab** — stable commercial iOS niche [S312]. Not a dependency.

## Code-reading queue

1. **heronarts/LX — model & fixture subsystem** (`heronarts.lx.model.LXModel`, `LXPoint`, `heronarts.lx.structure.JsonFixture`): confirm exact per-point fields (raw `x,y,z` vs normalized `xn,yn,zn`), how transforms compose, how outputs segment points. Answers: what a complete map data model needs. (License: LX Studio Software License — read-only study.)
2. **TheMariday/marimapper** (`marimapper/` backends + SfM pipeline, pin main@HEAD at read time): CSV schema, how interpolation/confidence is recorded, what a custom backend must implement. Answers: import-filter spec + pewpew backend feasibility [S300].
3. **LedFx/LedFx** (`ledfx/virtuals.py` + complex-segments implementation): the numpy scatter/gather compile of segments→devices. Answers: fastest Python runtime map representation [S011][S305].
4. **savdb/led_camera_map**: minimal Art-Net-blink + OpenCV detect loop (~small codebase, MIT — vendorable). Answers: how little code a built-in 2D camera mapper needs [S313].
5. **xLightsSequencer/xLights** (`xLights/models/CustomModel.cpp`, buffer styles in `RenderBuffer`): .xmodel XML schema for the import filter [S026].

## Open questions

- marimapper accuracy: no quantitative error figures published (README is qualitative) [S300]. Settle with a bench test: map a known-geometry strip/grid, compute RMS error vs ground truth.
- Exact LX per-point normalized-coordinate field names and normalization policy (Fill vs Contain equivalent) — needs the LX code read (queue item 1).
- Whether Chromatik/LX license permits studying code for reimplementation cleanly (clean-room the format spec from docs [S309] to be safe).
- Did zranger1's iOS mapping app ever ship (post-May-2024)? [S310] Forum re-check or ask.
- FPP VirtualDisplay per-pixel preview coordinate file format — worth a look only if FPP import ever matters [S308][NEEDS-VERIFICATION].
- Vitminee/wled-mapper maturity (commit history, whether the gap-mask export matches WLED 2d-gaps semantics) [S314].
- Pixelblaze coordinate precision (16-bit fixed point?) — forum thread 2062 suggests resolution limits on v3 maps; unconfirmed [S200][NEEDS-VERIFICATION].

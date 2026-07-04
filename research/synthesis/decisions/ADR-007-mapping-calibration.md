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
  portability convention in the hobby space.
- [S305][S630:ledfx/virtuals.py#L409-L495] LedFx's precompiled
  segment→device gathers ("up to 13× faster") — evidence for the compiled
  NumPy runtime representation.
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

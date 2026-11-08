// Generated from schemas/rig.v1.json by web/scripts/gen-types.ts; do not edit.
// Regenerate: `pnpm -C web gen-types`. The schema comes from src/pewpew/rig/models.py.

/**
 * A compiled rig as the engine sends it: the preview's `rig`, or the studio's compile body.
 */
export type RigJson = RigView | CompiledRig;

/**
 * The `rig` of the preview's `hello` and `layout`
 * (`pewpew.rig.runtime.rig_view`): what a 3D view needs to place each
 * fixture and its pixels. `frame` is C, which takes the file's y-up
 * meters to the plan frame: `mapping = (C @ p) * scale + shift`.
 */
export interface RigView {
  catalog_digest: string;
  frame: number[][];
  scale: number;
  shift: number[];
  plan: RigViewPlan | PlanMissing | null;
  fixtures: RigViewFixture[];
  types: {
    [k: string]: RigViewType;
  };
  controllers: ControllerTarget[];
  slices: OutputSlice[];
  controller_slices: ControllerSlice[];
  issues: Issue[];
}
/**
 * The floor plan of a `RigView`: its top-left corner in plan-frame
 * meters and its meters per image pixel. `url` is where the preview
 * serves the image: `rig_view` leaves it out, and the preview's
 * `View.of` adds it.
 */
export interface RigViewPlan {
  corner_m: number[];
  meters_per_pixel: number;
  url: string;
}
/**
 * A `RigView` plan whose image the preview cannot serve.
 */
export interface PlanMissing {
  error: string;
}
/**
 * One fixture of a `RigView`: its `FixtureInstance` without `chain`.
 */
export interface RigViewFixture {
  id: string;
  type_id: string;
  base_type_id: string;
  group: string | null;
  matrix: number[];
  pixel_start: number;
  pixel_count: number;
  controller: string | null;
  output: string | null;
  tags: string[];
  dims: {
    [k: string]: number;
  };
  attachments: {
    [k: string]: string | null;
  };
  attachment_matrices: {
    [k: string]: number[] | null;
  };
}
/**
 * A fixture type's pixels: `count` along its local y over `span_m`,
 * centred, `z_m` off its local z. `facing` is the light's local direction,
 * or null for a light that faces every way.
 */
export interface RigViewType {
  count: number;
  span_m: number;
  z_m: number;
  facing: number[] | null;
}
/**
 * One controller of a compiled rig and where DDP reaches it; None without a host.
 */
export interface ControllerTarget {
  id: string;
  profile: string;
  host: string | null;
  port: number | null;
}
/**
 * The contiguous pixels one controller output drives.
 */
export interface OutputSlice {
  controller: string;
  output: string;
  chain: string;
  start: number;
  count: number;
  led_type: number | null;
  color_order: string;
}
/**
 * The contiguous pixels one controller receives, for DDP.
 */
export interface ControllerSlice {
  controller: string;
  start: number;
  count: number;
}
/**
 * One finding. Errors stop a compile; violations and warnings do not.
 */
export interface Issue {
  level: "error" | "violation" | "warning";
  code: string;
  message: string;
  ref: string | null;
}
/**
 * `CompiledRig.to_json()`, the body of the studio's `POST /api/compile`
 * (`CompiledRig` in schemas/rig.v1.json).
 */
export interface CompiledRig {
  n: number;
  catalog_digest: string;
  fixtures: CompiledFixture[];
  slices: OutputSlice[];
  controller_slices: ControllerSlice[];
  feeds: Feed[];
  issues: Issue[];
  report: RigReport | null;
  positions_m: number[][];
  normals: number[][];
  controllers: ControllerTarget[];
  scale: number;
  shift: number[];
  plan: Plan | null;
  variants: Variant[];
}
/**
 * One fixture of a compiled rig (`CompiledFixture` in schemas/rig.v1.json).
 *
 * `matrix` is the world matrix as 16 floats in column-major order, the order
 * of three.js `Matrix4.elements` (https://threejs.org/docs/pages/Matrix4.html).
 * The fixture's pixels are `pixel_start .. pixel_start + pixel_count - 1`.
 * `attachment_matrices` gives each attachment's frame in world space.
 * `dims` and `tags` are the placement's own; with `dims`, `type_id` names
 * the variant type they compiled to and `base_type_id` the catalog type
 * it was made from (equal to `type_id` without dims).
 */
export interface CompiledFixture {
  id: string;
  type_id: string;
  base_type_id: string;
  group: string | null;
  matrix: number[];
  attachments: {
    [k: string]: string | null;
  };
  attachment_matrices: {
    [k: string]: number[] | null;
  };
  pixel_start: number;
  pixel_count: number;
  controller: string | null;
  output: string | null;
  chain: string | null;
  tags: string[];
  dims: {
    [k: string]: number;
  };
}
/**
 * A PSU feed into `count` fixtures of a chain, from index `first`.
 *
 * It injects at the input of fixture `first`, with V+ open toward the
 * upstream run (docs/studio/domain-model.md:50).
 */
export interface Feed {
  id: string;
  psu: string;
  chain: string;
  first: number;
  count: number;
  cable: string;
  length_m: number;
  fuse_a: number | null;
}
/**
 * The power, wiring and controller report (docs/studio/domain-model.md:228-243).
 */
export interface RigReport {
  target_fps: number | null;
  limits: AutoWiring;
  totals: Totals;
  controllers: ControllerReport[];
  outputs: OutputReport[];
  hops: HopReport[];
  feeds: FeedReport[];
  psus: PsuReport[];
  bom: BomLine[];
  basis: Basis[];
  notes: string[];
}
/**
 * Options for the deterministic auto-wiring (docs/studio/domain-model.md:217-226).
 *
 * The defaults are the design's: 3 m hop
 * (https://auschristmaslighting.com/threads/maximum-distance-between-ws2811-pixel-nodes.7607),
 * 75% loading of a fuse sized to the connector, Littelfuse's guidance as
 * RES-033 records it (the maintainer's private notes;
 * https://info.littelfuse.com/hubfs/Fuseology%20Design%20Guide.pdf),
 * 10% drop (https://quinled.info/the-ultimate-led-strip-power-injection-guide/)
 * and 80% PSU loading (https://flexfireleds.com/blog/LED-power-supply-derating).
 * The 1.2 slack is the design's example figure (docs/studio/domain-model.md:239);
 * it lengthens every straight cable run: data hops, leads and feeds.
 * `feed_cable` names the cable of every feed; None takes the catalog cable
 * with the lowest loop resistance per metre.
 */
export interface AutoWiring {
  target_fps: number;
  fixtures_per_output: number | null;
  max_hop_m: number;
  hop_slack: number;
  connector_load_fraction: number;
  max_drop_fraction: number;
  psu_load_fraction: number;
  feed_cable: string | null;
}
/**
 * The rig's draw at the nominal voltage.
 *
 * `worst_w` and `worst_a` have every channel of every fixture full.
 * `rgb_worst_w` and `rgb_worst_a` are the most the RGB stream draws
 * through each board's auto-white. `capped_w` and `capped_a` are that
 * under the power cap: what the PSUs are sized for. Each includes the
 * boards the PSUs power (`PsuReport.board_a`), whatever the frame.
 */
export interface Totals {
  fixtures: number;
  pixels: number;
  worst_w: number;
  worst_a: number;
  rgb_worst_w: number;
  rgb_worst_a: number;
  capped_w: number;
  capped_a: number;
  controllers: number;
  psus: number;
  feeds: number;
}
export interface ControllerReport {
  id: string;
  profile: string;
  derived: boolean;
  outputs: number;
  outputs_used: number;
  pixels: number;
}
/**
 * One output: its pixels and frame time, the frame rate the wire allows,
 * and `fps`, the rate it shows: at most the firmware's `min_frame_interval_s`.
 */
export interface OutputReport {
  controller: string;
  output: string;
  chain: string;
  pixels: number;
  led_type: number | null;
  led_label: string | null;
  frame_s: number;
  wire_fps: number;
  fps: number;
}
/**
 * One data cable: a controller's `lead` to a chain, or a `link` between fixtures.
 *
 * `run_m` is the straight distance × slack; `path_m` adds the pigtails. On a
 * `tee` chain a link runs from input to input along the trunk, and `path_m`
 * also adds the source fixture's return to its input (`tee_link_m`).
 */
export interface HopReport {
  chain: string;
  kind: "lead" | "link";
  source: string;
  target: string;
  run_m: number;
  path_m: number;
}
/**
 * One feed. `loop_ohm` is its cable's V+ and GND; `drop_v` is at its last fixture.
 *
 * `current_a` has every channel full; the drop uses it. `capped_a` is the
 * RGB worst case under the power cap; the PSU loads use it. The connector
 * check and `fuse_window_a` take `capped_a` under a cap, else `current_a`.
 * `connector_a` is the least rating of the fixtures' input connectors and
 * the PSU's output connector.
 */
export interface FeedReport {
  id: string;
  psu: string;
  chain: string;
  fixtures: string[];
  cable: string;
  length_m: number;
  current_a: number;
  capped_a: number;
  connector_a: number | null;
  fuse_a: number | null;
  /**
   * @minItems 2
   * @maxItems 2
   */
  fuse_window_a: [number, number | null];
  loop_ohm: number;
  drop_v: number;
  drop_fraction: number;
  va: number;
  note: string | null;
}
/**
 * One PSU. `current_a`, `load_fraction` and `watts` are its load from the
 * RGB stream under the power cap; `worst_a` is its load with every channel full.
 * Both include `board_a`, what the boards it `powers` draw through their buck.
 */
export interface PsuReport {
  id: string;
  type: string;
  derived: boolean;
  v_out: number;
  i_max_a: number;
  current_a: number;
  worst_a: number;
  load_fraction: number;
  watts: number;
  feeds: string[];
  powers: string[];
  board_a: number;
}
/**
 * One line of the bill of materials. Cables give the total `length_m`.
 */
export interface BomLine {
  kind: "fixture" | "attachment" | "controller" | "component" | "psu" | "fuse" | "cable";
  item: string;
  name: string;
  count: number;
  length_m: number | null;
}
/**
 * One unmeasured value that results rest on, with its source.
 */
export interface Basis {
  fact: string;
  v: unknown;
  status: "measured" | "stated" | "inferred" | "derived" | "assumed";
  src: string | null;
  used_for: string[];
}
/**
 * A floor-plan image, calibrated by two image pixels `meters` apart.
 */
export interface Plan {
  image: string;
  /**
   * @minItems 2
   * @maxItems 2
   */
  points: [[number, number], [number, number]];
  meters: number;
  /**
   * @minItems 2
   * @maxItems 2
   */
  at?: [number, number];
}
/**
 * A fixture type made from `type` with some dims replaced. `dims` holds
 * every dim of the variant, evaluated.
 */
export interface Variant {
  id: string;
  type: string;
  dims: {
    [k: string]: number;
  };
}

/**
 * Types for the studio API.
 *
 * `Issue`, `IssueLevel` and `SavedArrangement` come from the OpenAPI spec
 * through orval (src/studio/api/generated). The spec types the arrangement, catalog
 * and compile bodies as free-form objects, so the rest is written by hand
 * after the pydantic models (src/pewpew/rig/models.py: `Pose`, `RingGroup`,
 * `ArrayGroup`, `FixtureInstance`; `Catalog.to_json` in
 * src/pewpew/rig/catalog.py).
 */
import type { IssueModel } from "./generated/model";

export type {
  IssueModelLevel as IssueLevel,
  SavedArrangement,
} from "./generated/model";

export type Issue = IssueModel;

export type Vec3 = [number, number, number];
export type QuatXYZW = [number, number, number, number];

/** A rotation from the fixture's +y direction and a roll about it. */
export interface Aim {
  axis: Vec3;
  roll_deg?: number;
}

/** `T(position_m)·R`; R from `quat_xyzw` or `aim`, else the identity. The studio writes quaternions. */
export interface Pose {
  position_m?: Vec3;
  quat_xyzw?: QuatXYZW | null;
  aim?: Aim | null;
}

/** An attachment type id, or null for a bare end. */
export type AttachmentRef = string | null;

/** Anchor name to attachment type; the bar's ends are `end_a` and `end_b`. */
export type EndAttach = Record<string, AttachmentRef>;

export interface FixtureEntry {
  id: string;
  type: string;
  dims?: Record<string, number>;
  tags?: string[];
  pose?: Pose;
  attach?: EndAttach;
}

export type DataIn = "inner" | "outer";

export interface RingGroup {
  id: string;
  preset: "ring";
  type: string;
  count: number;
  start_radius_m: number;
  angle_offset_deg?: number;
  tilt_deg?: number;
  roll_deg?: number;
  data_in?: DataIn;
  attach?: { inner?: AttachmentRef; outer?: AttachmentRef };
  pose?: Pose;
}

/** Member (i, j) sits at i·steps_m[0] + j·steps_m[1], then takes `member`; k = i·counts[1] + j. */
export interface ArrayGroup {
  id: string;
  preset: "array";
  type: string;
  counts: [number] | [number, number];
  steps_m: Vec3[];
  member?: Pose;
  attach?: EndAttach;
  pose?: Pose;
}

export type Group = RingGroup | ArrayGroup;

/** Parts of the file the browser passes through without reading. */
export type Opaque = Record<string, unknown>;

/**
 * The software power cap (`PowerLimit` in src/pewpew/rig/models.py). The
 * engine scales every frame by `max_brightness`, then holds the estimated
 * draw at or under `max_watts`. Omitted, it caps nothing.
 */
export interface PowerLimit {
  /** Watts, over 0 and at most 1e6; null or absent caps no watts. */
  max_watts?: number | null;
  /** 0 to 1; absent is 1. */
  max_brightness?: number;
}

export interface Arrangement {
  format: "pewpew.arrangement";
  version: number;
  name?: string;
  fixtures: FixtureEntry[];
  groups: Group[];
  controllers?: Opaque[];
  psus?: Opaque[];
  wiring?: Opaque;
  power?: PowerLimit;
}

export interface CatalogAnchor {
  accepts?: string | null;
  connector?: string | null;
}

export interface CatalogFixtureType {
  id: string;
  name: string;
  /** Null on a server that cannot build geometry. */
  digest: string | null;
  assembly_url: string | null;
  anchors?: Record<string, CatalogAnchor>;
  [key: string]: unknown;
}

export interface CatalogAttachmentType {
  id: string;
  name: string;
  /** Null on a server that cannot build geometry. */
  digest: string | null;
  assembly_url: string | null;
  fits?: string;
  [key: string]: unknown;
}

export interface CatalogEntry {
  id: string;
  name: string;
  [key: string]: unknown;
}

export interface PresetInfo {
  name: string;
  doc?: string;
  params: Array<{ name: string; required: boolean; default?: unknown }>;
}

export interface Catalog {
  digest?: string;
  fixture_types: CatalogFixtureType[];
  attachment_types: CatalogAttachmentType[];
  controllers: CatalogEntry[];
  psus: CatalogEntry[];
  cables: CatalogEntry[];
  presets: PresetInfo[];
}

export interface CompiledFixture {
  id: string;
  /** The type id the catalog overlay knows: a variant id when the placement gave dims. */
  type_id: string;
  /** The catalog type the fixture is made from. */
  base_type_id?: string;
  dims?: Record<string, number>;
  tags?: string[];
  /** The group this fixture was expanded from, or null for a free fixture. */
  group?: string | null;
  /** 16 floats, column-major, three.js `Matrix4.elements` order. */
  matrix: number[];
  attachments: Record<string, AttachmentRef>;
  /** Each attachment's frame in world space: origin on the anchor, +y along its direction. */
  attachment_matrices?: Record<string, number[] | null>;
  pixel_start: number;
  pixel_count: number;
}

export interface OutputSlice {
  controller: string;
  output: string;
  start: number;
  count: number;
  led_type: number | null;
  color_order: string;
}

/** Workstream 2 owns the report's fields; the panel renders any JSON. */
export type RigReport = Record<string, unknown>;

export interface CompiledRig {
  n: number;
  catalog_digest: string;
  fixtures: CompiledFixture[];
  slices: OutputSlice[];
  report: RigReport | null;
  issues: Issue[];
}

/** One look in the looks file's form (version 4), as `GET /api/looks` gives
 * each: the engine checks it whole, so the page passes it through. */
export type LookDocument = Opaque & { layers: unknown[] };

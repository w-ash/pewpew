/**
 * Types for the studio API.
 *
 * `Issue`, `IssueLevel` and `SavedArrangement` come from the OpenAPI spec
 * through orval (src/api/generated). The spec types the arrangement, catalog
 * and compile bodies and the pattern params as free-form objects, so the rest
 * is written by hand after the pydantic models (src/pewpew/rig/models.py:
 * `Pose`, `RingGroup`, `ArrayGroup`, `FixtureInstance`; `Catalog.to_json` in
 * src/pewpew/rig/catalog.py; `ParamSet.describe` in src/pewpew/pattern.py).
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
  type_id: string;
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

/** A catalog or report fact with provenance (domain-model.md §1). */
export interface Sourced {
  v: unknown;
  status: "measured" | "stated" | "inferred" | "derived" | "assumed";
  src?: string;
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

/** A color param's value: hue in degrees, saturation and brightness in 0..1. */
export interface Hsv {
  h: number;
  s: number;
  v: number;
}

/** One stop of a palette: its place `at` from 0 to 1, and its color. */
export interface GradientStop extends Hsv {
  at: number;
}

/** A palette param's value: a label ("" for none) and 2 or more stops in
 * order of `at`, the first at 0 and the last at 1. */
export interface Gradient {
  label: string;
  stops: GradientStop[];
}

/** A param value in its JSON form, as `ParamSet.snapshot_json()` gives it. */
export type ParamValue = number | boolean | string | Hsv | Gradient;

/** The numeric fields of a float, an int, or one part of a color. */
export interface NumberSpec {
  lo: number;
  hi: number;
  step: number;
  decimals: number;
  unit: string;
  periodic: boolean;
}

/** The fields every param record has (`Param.spec()`, src/pewpew/params/kinds.py). */
interface ParamCommon {
  name: string;
  label: string;
  help: string;
  group: string;
  widget: string;
}

export interface FloatParam extends ParamCommon, NumberSpec {
  kind: "float";
  default: number;
}
export interface IntParam extends ParamCommon, NumberSpec {
  kind: "int";
  default: number;
}
export interface BoolParam extends ParamCommon {
  kind: "bool";
  default: boolean;
}
export interface ChoiceParam extends ParamCommon {
  kind: "choice";
  default: string;
  options: { value: string; label: string }[];
}
export interface ColorParam extends ParamCommon {
  kind: "color";
  default: Hsv;
  parts: Record<"h" | "s" | "v", NumberSpec & { label: string }>;
}
export interface PaletteParam extends ParamCommon {
  kind: "palette";
  default: Gradient;
  /** The numeric fields of a stop's place and color parts. */
  stop: Record<"at" | "h" | "s" | "v", NumberSpec & { label: string }>;
  max_stops: number;
  /** The gradients a control offers, by label; a label sets its preset. */
  presets: { value: Gradient; label: string }[];
}
/** A record of a kind this page does not know: shown, never set. */
export interface UnknownParam extends ParamCommon {
  kind: "unknown";
  default: unknown;
}

/** One param record, as the engine declares it, by `kind`. */
export type ParamSpec =
  | FloatParam
  | IntParam
  | BoolParam
  | ChoiceParam
  | ColorParam
  | PaletteParam
  | UnknownParam;

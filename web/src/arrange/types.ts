/**
 * The arrangement file as the editor reads and writes it, written by hand
 * after the pydantic models (src/pewpew/rig/models.py: `Arrangement`,
 * `Pose`, `RingGroup`, `ArrayGroup`, `PowerLimit`). The engine validates
 * the whole file; the editor reads only these parts.
 */
import type { Issue } from "../rig/types.gen";
import type { Vec3 } from "../rig/parts";

export type { Issue, RigReport } from "../rig/types.gen";
export type { PartsCatalog, Vec3 } from "../rig/parts";

export type IssueLevel = Issue["level"];

export type QuatXYZW = [number, number, number, number];

/** A rotation from the fixture's +y direction and a roll about it. */
export interface Aim {
  axis: Vec3;
  roll_deg?: number;
}

/** `T(position_m)·R`; R from `quat_xyzw` or `aim`, else the identity. The editor writes quaternions. */
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

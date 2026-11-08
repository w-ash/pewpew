import { useEffect } from "react";
import { Matrix4, Quaternion, Vector3 } from "three";
import { groupOf, type Placed, type Selection } from "../arrange/arrangement";
import { matrixPose, type PoseQ } from "../arrange/pose";
import { sameJson } from "../arrange/sync";
import type { Aim, Arrangement, Pose } from "../arrange/types";

/**
 * A gizmo drag in progress: `delta` is the motion since the view last drew `fixtures` from the server,
 * applied on top of their server matrices until the compile of what it committed settles
 * (`useSettledPreview`, the studio's). A new drag of the same fixtures before then adds to the motion it
 * holds, so it starts where the last one left them. On the Console, `offsets` move each fixture from the
 * pose the server drew it at to the one the editor holds (`presentOffsets`), so an edit, an undo or a
 * redo shows at once; a drag then ends as it commits.
 */
export const dragPreview = {
  delta: null as Matrix4 | null,
  fixtures: new Set<number>(),
  /** By compiled fixture index, the motion from its server matrix to its pose in the editor; null for none. */
  offsets: null as ReadonlyMap<number, Matrix4> | null,
  version: 0,
  /** The motion held when the drag began. */
  start: new Matrix4(),
  begin(fixtures: Iterable<number>) {
    const next = new Set(fixtures);
    const same = this.delta !== null && next.size === this.fixtures.size && [...next].every((i) => this.fixtures.has(i));
    this.start = same && this.delta ? this.delta.clone() : new Matrix4();
    this.fixtures = next;
    this.delta = this.start.clone();
    this.version++;
  },
  /** The proxy moved by `delta` since this drag began. */
  move(delta: Matrix4) {
    this.delta = new Matrix4().multiplyMatrices(delta, this.start);
    this.version++;
  },
  clear() {
    if (this.delta === null && this.fixtures.size === 0) return;
    this.delta = null;
    this.fixtures = new Set();
    this.start = new Matrix4();
    this.version++;
  },
  /** Draw each fixture `offsets` names moved by its offset, or each at its server matrix for null. */
  offset(offsets: ReadonlyMap<number, Matrix4> | null) {
    if (offsets === this.offsets || (!offsets?.size && !this.offsets?.size)) return;
    this.offsets = offsets;
    this.version++;
  },
};

/** The rotation whose +y is `axis`, rolled by `roll_deg` about it, as the engine makes it
 * (src/pewpew/rig/pose.py `aim`); null for an axis that is zero or not finite. */
function aimMatrix({ axis, roll_deg = 0 }: Aim): Matrix4 | null {
  const y = new Vector3(...axis);
  const length = y.length();
  if (!(length > 0 && Number.isFinite(length))) return null;
  y.divideScalar(length);
  // The reference is world +Y, or world +Z when the axis is within about 2.6° of vertical.
  const ref = Math.abs(y.y) > 0.999 ? new Vector3(0, 0, 1) : new Vector3(0, 1, 0);
  const z = ref.addScaledVector(y, -ref.dot(y)).normalize();
  const x = new Vector3().crossVectors(y, z);
  return new Matrix4().makeBasis(x, y, z).multiply(new Matrix4().makeRotationY((roll_deg * Math.PI) / 180));
}

/** The matrix of a file pose, `T(position_m)·R`, as the engine makes it; null for a rotation it cannot be. */
function poseMatrix(pose: Pose | undefined): Matrix4 | null {
  const q = pose?.quat_xyzw;
  const r = q
    ? new Matrix4().makeRotationFromQuaternion(new Quaternion(...q).normalize())
    : pose?.aim
      ? aimMatrix(pose.aim)
      : new Matrix4();
  return r?.setPosition(...(pose?.position_m ?? [0, 0, 0])) ?? null;
}

/** The pose of free fixture `selection` as `arrangement` holds it, one placed by `aim` included; null for
 * a group or a fixture it does not hold. */
export function heldPose(arrangement: Arrangement, selection: Selection): PoseQ | null {
  const entry = selection.kind === "fixture" ? arrangement.fixtures.find((f) => f.id === selection.id) : undefined;
  const m = entry ? poseMatrix(entry.pose) : null;
  return m ? matrixPose(m.elements) : null;
}

/** Whether `m` moves nothing, to within float error. */
function still(m: Matrix4): boolean {
  const I = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  return m.elements.every((v, i) => Math.abs(v - I[i]!) < 1e-6);
}

/**
 * For each of the server's `fixtures`, the motion from its matrix to its pose in `present`, the editor's
 * arrangement, where they differ. A free fixture's matrix is its pose, so its offset is that pose over
 * the matrix. A group member's is the group's pose in `present` over its pose in `engine`, the
 * arrangement the server compiled, while the rest of the group is the same in both. A fixture `present`
 * no longer holds stays where the server drew it.
 */
export function presentOffsets(
  fixtures: readonly Placed[],
  present: Arrangement,
  engine: Arrangement | null,
): Map<number, Matrix4> {
  const out = new Map<number, Matrix4>();
  const groups = new Map<string, Matrix4 | null>();
  const groupOffset = (id: string): Matrix4 | null => {
    if (groups.has(id)) return groups.get(id)!;
    const now = present.groups.find((g) => g.id === id);
    const then = engine?.groups.find((g) => g.id === id);
    let m: Matrix4 | null = null;
    if (now && then && sameShape(now, then)) {
      const a = poseMatrix(now.pose), b = poseMatrix(then.pose);
      if (a && b) m = a.multiply(b.invert());
    }
    groups.set(id, m);
    return m;
  };
  const scratch = new Matrix4();
  fixtures.forEach((f, i) => {
    const group = groupOf(f);
    let m: Matrix4 | null;
    if (group) m = groupOffset(group);
    else {
      const entry = present.fixtures.find((e) => e.id === f.id);
      m = entry ? poseMatrix(entry.pose) : null;
      m?.multiply(scratch.fromArray(f.matrix).invert());
    }
    if (m && !still(m)) out.set(i, m);
  });
  return out;
}

/** Whether groups `a` and `b` are the same but for their pose: their members sit alike within them. */
function sameShape(a: object, b: object): boolean {
  const { pose: _a, ...ra } = a as { pose?: unknown };
  const { pose: _b, ...rb } = b as { pose?: unknown };
  return sameJson(ra, rb);
}

/** Ends the drag preview when `answered` turns true: the server has answered for the current arrangement,
 * so the view shows its compile, or keeps the last good one after a refusal. Either way the preview has no
 * pose left to bridge, and one kept would draw a pose the document does not hold. */
export function useSettledPreview(answered: boolean) {
  useEffect(() => {
    if (answered) dragPreview.clear();
  }, [answered]);
}

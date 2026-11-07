/**
 * Pose conversions for the editor.
 *
 * The file format stores rotations as xyzw quaternions with w ≥ 0 and never
 * stores Euler angles (docs/studio/domain-model.md §3). The inspector shows
 * yaw, pitch and roll in degrees as three.js Euler order "YXZ": yaw about +Y,
 * then pitch about the new +X, then roll about the new +Z. All zeros is the
 * identity pose, a bar standing upright with its LEDs facing +Z.
 */
import { Euler, MathUtils, Matrix4, Quaternion, Vector3 } from "three";
import type { Pose, QuatXYZW, Vec3 } from "@/api/types";

/** A pose with both parts given, as the editor reads and writes it. */
export interface PoseQ {
  position_m: Vec3;
  quat_xyzw: QuatXYZW;
}

export const IDENTITY_POSE: PoseQ = {
  position_m: [0, 0, 0],
  quat_xyzw: [0, 0, 0, 1],
};

/**
 * A file pose with its defaults filled in, or null when its rotation is an
 * `aim`, which only the server resolves.
 */
export function resolvePose(pose: Pose | undefined): PoseQ | null {
  if (pose?.aim) return null;
  return {
    position_m: pose?.position_m ?? [0, 0, 0],
    quat_xyzw: pose?.quat_xyzw ?? [0, 0, 0, 1],
  };
}

export const EULER_ORDER = "YXZ" as const;

export interface YawPitchRoll {
  yaw: number;
  pitch: number;
  roll: number;
}

/** Unit length, w ≥ 0, and -0 folded to 0, so equal rotations store equal bytes. */
export function canonicalQuat(q: readonly number[]): QuatXYZW {
  let [x, y, z, w] = q;
  const len = Math.hypot(x, y, z, w);
  if (!(len > 0)) return [0, 0, 0, 1];
  x /= len;
  y /= len;
  z /= len;
  w /= len;
  if (
    w < 0 ||
    (w === 0 && (x < 0 || (x === 0 && (y < 0 || (y === 0 && z < 0)))))
  ) {
    x = -x;
    y = -y;
    z = -z;
    w = -w;
  }
  return [x + 0, y + 0, z + 0, w + 0];
}

export function quatToYpr(q: QuatXYZW): YawPitchRoll {
  const e = new Euler().setFromQuaternion(
    new Quaternion(q[0], q[1], q[2], q[3]),
    EULER_ORDER,
  );
  return {
    yaw: MathUtils.radToDeg(e.y) + 0,
    pitch: MathUtils.radToDeg(e.x) + 0,
    roll: MathUtils.radToDeg(e.z) + 0,
  };
}

export function yprToQuat({ yaw, pitch, roll }: YawPitchRoll): QuatXYZW {
  const q = new Quaternion().setFromEuler(
    new Euler(
      MathUtils.degToRad(pitch),
      MathUtils.degToRad(yaw),
      MathUtils.degToRad(roll),
      EULER_ORDER,
    ),
  );
  return canonicalQuat([q.x, q.y, q.z, q.w]);
}

/** `T(p)·R(q)` as a three.js matrix. */
export function poseMatrix(pose: PoseQ): Matrix4 {
  const [x, y, z, w] = pose.quat_xyzw;
  return new Matrix4().compose(
    new Vector3(...pose.position_m),
    new Quaternion(x, y, z, w),
    new Vector3(1, 1, 1),
  );
}

/** The pose of a rigid column-major matrix, such as a server fixture matrix. */
export function matrixPose(elements: readonly number[]): PoseQ {
  const p = new Vector3();
  const q = new Quaternion();
  new Matrix4().fromArray(elements as number[]).decompose(p, q, new Vector3());
  return {
    position_m: [p.x + 0, p.y + 0, p.z + 0],
    quat_xyzw: canonicalQuat([q.x, q.y, q.z, q.w]),
  };
}

/** Rounds to 0.1 mm, below the 1 cm snap, so poses read cleanly in files. */
export function roundVec(v: readonly number[]): Vec3 {
  const r = (n: number) => Math.round(n * 1e4) / 1e4 + 0;
  return [r(v[0]), r(v[1]), r(v[2])];
}

/**
 * The pose with its data direction reversed: a half turn about local +Z,
 * which keeps the LED facing. q·(0, 0, 1, 0) written out, so it is exact.
 */
export function flipPose(pose: PoseQ): PoseQ {
  const [x, y, z, w] = pose.quat_xyzw;
  return { ...pose, quat_xyzw: canonicalQuat([y, -x, w, -z]) };
}

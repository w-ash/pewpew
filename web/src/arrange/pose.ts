/**
 * Pose conversions for the editor.
 *
 * The file format stores rotations as xyzw quaternions with w ≥ 0 and never
 * stores Euler angles (docs/studio/domain-model.md §3). The inspector shows
 * yaw, pitch and roll in degrees as three.js Euler order "YXZ": yaw about +Y,
 * then pitch about the new +X, then roll about the new +Z. All zeros is the
 * identity pose, a bar standing upright with its LEDs facing +Z.
 *
 * The math is three.js's own (`Euler.setFromQuaternion`, `Quaternion.setFromEuler`,
 * `Matrix4.decompose`), written out so the editor loads without three.js:
 * only the 3D view loads it (test/arrange/pose.test.ts compares the two).
 */
import type { Pose, QuatXYZW, Vec3 } from "./types";

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
 * `aim`, which only the engine resolves.
 */
export function resolvePose(pose: Pose | undefined): PoseQ | null {
  if (pose?.aim) return null;
  return {
    position_m: pose?.position_m ?? [0, 0, 0],
    quat_xyzw: pose?.quat_xyzw ?? [0, 0, 0, 1],
  };
}

export interface YawPitchRoll {
  yaw: number;
  pitch: number;
  roll: number;
}

const RAD2DEG = 180 / Math.PI;
const DEG2RAD = Math.PI / 180;

/** Unit length, w ≥ 0, and -0 folded to 0, so equal rotations store equal bytes. */
export function canonicalQuat(q: readonly [number, number, number, number]): QuatXYZW {
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

/** The rotation matrix of `q`, row by row: [m11, m12, m13, m21, …, m33]. */
function rotation([x, y, z, w]: readonly number[]): number[] {
  const x2 = x! + x!, y2 = y! + y!, z2 = z! + z!;
  const xx = x! * x2, xy = x! * y2, xz = x! * z2;
  const yy = y! * y2, yz = y! * z2, zz = z! * z2;
  const wx = w! * x2, wy = w! * y2, wz = w! * z2;
  return [
    1 - (yy + zz), xy - wz, xz + wy,
    xy + wz, 1 - (xx + zz), yz - wx,
    xz - wy, yz + wx, 1 - (xx + yy),
  ];
}

export function quatToYpr(q: QuatXYZW): YawPitchRoll {
  const [m11, , m13, m21, m22, m23, m31, , m33] = rotation(q) as [number, number, number, number, number, number, number, number, number];
  const pitch = Math.asin(-Math.min(Math.max(m23, -1), 1));
  const free = Math.abs(m23) < 0.9999999;
  const yaw = free ? Math.atan2(m13, m33) : Math.atan2(-m31, m11);
  const roll = free ? Math.atan2(m21, m22) : 0;
  return { yaw: yaw * RAD2DEG + 0, pitch: pitch * RAD2DEG + 0, roll: roll * RAD2DEG + 0 };
}

export function yprToQuat({ yaw, pitch, roll }: YawPitchRoll): QuatXYZW {
  const half = (deg: number) => (deg * DEG2RAD) / 2;
  const c1 = Math.cos(half(pitch)), c2 = Math.cos(half(yaw)), c3 = Math.cos(half(roll));
  const s1 = Math.sin(half(pitch)), s2 = Math.sin(half(yaw)), s3 = Math.sin(half(roll));
  return canonicalQuat([
    s1 * c2 * c3 + c1 * s2 * s3,
    c1 * s2 * c3 - s1 * c2 * s3,
    c1 * c2 * s3 - s1 * s2 * c3,
    c1 * c2 * c3 + s1 * s2 * s3,
  ]);
}

/** The quaternion of a rotation matrix given row by row (`rotation`'s order). */
function quatOf(m: readonly number[]): [number, number, number, number] {
  const [m11, m12, m13, m21, m22, m23, m31, m32, m33] = m as [number, number, number, number, number, number, number, number, number];
  const trace = m11 + m22 + m33;
  if (trace > 0) {
    const s = 0.5 / Math.sqrt(trace + 1);
    return [(m32 - m23) * s, (m13 - m31) * s, (m21 - m12) * s, 0.25 / s];
  }
  if (m11 > m22 && m11 > m33) {
    const s = 2 * Math.sqrt(1 + m11 - m22 - m33);
    return [0.25 * s, (m12 + m21) / s, (m13 + m31) / s, (m32 - m23) / s];
  }
  if (m22 > m33) {
    const s = 2 * Math.sqrt(1 + m22 - m11 - m33);
    return [(m12 + m21) / s, 0.25 * s, (m23 + m32) / s, (m13 - m31) / s];
  }
  const s = 2 * Math.sqrt(1 + m33 - m11 - m22);
  return [(m13 + m31) / s, (m23 + m32) / s, 0.25 * s, (m21 - m12) / s];
}

/** The pose of a rigid column-major matrix, such as an engine fixture matrix. */
export function matrixPose(e: readonly number[]): PoseQ {
  const at = (i: number) => e[i] ?? 0;
  const det =
    at(0) * (at(5) * at(10) - at(9) * at(6)) -
    at(4) * (at(1) * at(10) - at(9) * at(2)) +
    at(8) * (at(1) * at(6) - at(5) * at(2));
  const sx = Math.hypot(at(0), at(1), at(2)) * (det < 0 ? -1 : 1);
  const sy = Math.hypot(at(4), at(5), at(6));
  const sz = Math.hypot(at(8), at(9), at(10));
  const q = quatOf([
    at(0) / sx, at(4) / sy, at(8) / sz,
    at(1) / sx, at(5) / sy, at(9) / sz,
    at(2) / sx, at(6) / sy, at(10) / sz,
  ]);
  return {
    position_m: [at(12) + 0, at(13) + 0, at(14) + 0],
    quat_xyzw: canonicalQuat(q),
  };
}

/** Rounds to 0.1 mm, below the 1 cm snap, so poses read cleanly in files. */
export function roundVec(v: readonly [number, number, number]): Vec3 {
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

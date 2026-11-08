import { Euler, MathUtils, Matrix4, Quaternion, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import type { QuatXYZW } from "../../src/arrange/types";
import {
  canonicalQuat,
  flipPose,
  matrixPose,
  type PoseQ,
  quatToYpr,
  yprToQuat,
} from "../../src/arrange/pose";

/** `T(p)·R(q)` as three.js composes it. */
const poseMatrix = (pose: PoseQ) =>
  new Matrix4().compose(new Vector3(...pose.position_m), new Quaternion(...pose.quat_xyzw), new Vector3(1, 1, 1));

const close = (a: readonly number[], b: readonly number[], eps = 1e-9) =>
  a.every((v, i) => Math.abs(v - b[i]!) < eps);

describe("canonicalQuat", () => {
  it("normalizes and makes w non-negative", () => {
    expect(canonicalQuat([0, 0, 0, -2])).toEqual([0, 0, 0, 1]);
    const q = canonicalQuat([0.5, 0.5, 0.5, -0.5]);
    expect(q).toEqual([-0.5, -0.5, -0.5, 0.5]);
  });

  it("picks one sign for a half turn, where w is zero", () => {
    expect(canonicalQuat([0, 0, -1, 0])).toEqual([0, 0, 1, 0]);
    expect(canonicalQuat([0, 0, 1, 0])).toEqual([0, 0, 1, 0]);
  });

  it("never stores negative zero", () => {
    const q = canonicalQuat([-0, -0, -0, 1]);
    expect(q.every((v) => !Object.is(v, -0))).toBe(true);
  });
});

describe("yaw, pitch and roll", () => {
  it("is the identity at zero", () => {
    expect(yprToQuat({ yaw: 0, pitch: 0, roll: 0 })).toEqual([0, 0, 0, 1]);
    expect(quatToYpr([0, 0, 0, 1])).toEqual({ yaw: 0, pitch: 0, roll: 0 });
  });

  it("turns yaw about +Y, pitch about +X and roll about +Z", () => {
    const up = (q: QuatXYZW, v: Vector3) =>
      v.clone().applyQuaternion(new Quaternion(...q));
    const yaw = yprToQuat({ yaw: 90, pitch: 0, roll: 0 });
    expect(close(up(yaw, new Vector3(0, 0, 1)).toArray(), [1, 0, 0])).toBe(
      true,
    );
    const pitch = yprToQuat({ yaw: 0, pitch: 90, roll: 0 });
    expect(close(up(pitch, new Vector3(0, 1, 0)).toArray(), [0, 0, 1])).toBe(
      true,
    );
    const roll = yprToQuat({ yaw: 0, pitch: 0, roll: 90 });
    expect(close(up(roll, new Vector3(0, 1, 0)).toArray(), [-1, 0, 0])).toBe(
      true,
    );
  });

  it("matches three.js Euler order YXZ", () => {
    const q = yprToQuat({ yaw: 30, pitch: -20, roll: 45 });
    const ref = new Quaternion().setFromEuler(
      new Euler(
        MathUtils.degToRad(-20),
        MathUtils.degToRad(30),
        MathUtils.degToRad(45),
        "YXZ",
      ),
    );
    expect(close(q, canonicalQuat([ref.x, ref.y, ref.z, ref.w]))).toBe(true);
  });

  it("round-trips away from gimbal lock", () => {
    for (const ypr of [
      { yaw: 10, pitch: 20, roll: 30 },
      { yaw: -170, pitch: 80, roll: -5 },
      { yaw: 135, pitch: -45, roll: 179 },
    ]) {
      const back = quatToYpr(yprToQuat(ypr));
      expect(back.yaw).toBeCloseTo(ypr.yaw, 9);
      expect(back.pitch).toBeCloseTo(ypr.pitch, 9);
      expect(back.roll).toBeCloseTo(ypr.roll, 9);
    }
  });

  it("stores w ≥ 0 even when the angles land on the other hemisphere", () => {
    expect(
      yprToQuat({ yaw: 270, pitch: 0, roll: 0 })[3],
    ).toBeGreaterThanOrEqual(0);
    expect(
      yprToQuat({ yaw: 0, pitch: 0, roll: -359 })[3],
    ).toBeGreaterThanOrEqual(0);
  });
});

describe("poses and matrices", () => {
  it("decomposes a server matrix back to the pose that made it", () => {
    const pose = {
      position_m: [1.25, -0.5, 2] as [number, number, number],
      quat_xyzw: yprToQuat({ yaw: 40, pitch: 10, roll: -70 }),
    };
    const back = matrixPose(poseMatrix(pose).elements);
    expect(back.position_m).toEqual(pose.position_m);
    expect(close(back.quat_xyzw, pose.quat_xyzw, 1e-7)).toBe(true);
  });

  it("flips data direction by a half turn about Z, keeping position and LED facing", () => {
    const pose = {
      position_m: [1, 2, 3] as [number, number, number],
      quat_xyzw: yprToQuat({ yaw: 25, pitch: 15, roll: 0 }),
    };
    const flipped = flipPose(pose);
    const m0 = poseMatrix(pose);
    const m1 = poseMatrix(flipped);
    const axis = (m: Matrix4, i: number) =>
      new Vector3().setFromMatrixColumn(m, i).toArray();
    expect(flipped.position_m).toEqual(pose.position_m);
    expect(
      close(
        axis(m1, 1),
        axis(m0, 1).map((v) => -v),
      ),
    ).toBe(true);
    expect(close(axis(m1, 2), axis(m0, 2))).toBe(true);
    expect(close(flipPose(flipped).quat_xyzw, pose.quat_xyzw)).toBe(true);
  });
});

describe("the math is three.js's", () => {
  // Deterministic sample rotations: a seeded LCG over each axis.
  let seed = 7;
  const next = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648) * 2 - 1;
  const quats = Array.from({ length: 200 }, () => canonicalQuat([next(), next(), next(), next()]));

  it("reads yaw, pitch and roll as Euler YXZ does", () => {
    for (const q of [...quats, [0, Math.SQRT1_2, 0, Math.SQRT1_2] as QuatXYZW, [Math.SQRT1_2, 0, 0, Math.SQRT1_2] as QuatXYZW]) {
      const e = new Euler().setFromQuaternion(new Quaternion(...q), "YXZ");
      const ypr = quatToYpr(q);
      expect(close([ypr.yaw, ypr.pitch, ypr.roll], [e.y, e.x, e.z].map(MathUtils.radToDeg), 1e-9)).toBe(true);
    }
  });

  it("makes a quaternion as setFromEuler does", () => {
    for (const q of quats) {
      const ypr = quatToYpr(q);
      const e = new Euler(MathUtils.degToRad(ypr.pitch), MathUtils.degToRad(ypr.yaw), MathUtils.degToRad(ypr.roll), "YXZ");
      const ref = new Quaternion().setFromEuler(e);
      expect(close(yprToQuat(ypr), canonicalQuat([ref.x, ref.y, ref.z, ref.w]), 1e-12)).toBe(true);
    }
  });

  it("decomposes a matrix as Matrix4.decompose does", () => {
    for (const q of quats) {
      const m = poseMatrix({ position_m: [next(), next(), next()], quat_xyzw: q });
      const p = new Vector3(), r = new Quaternion();
      m.decompose(p, r, new Vector3());
      const pose = matrixPose(m.elements);
      expect(pose.position_m).toEqual(p.toArray());
      expect(close(pose.quat_xyzw, canonicalQuat([r.x, r.y, r.z, r.w]), 1e-12)).toBe(true);
    }
  });
});

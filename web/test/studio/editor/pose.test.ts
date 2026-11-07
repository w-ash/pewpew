import { Euler, MathUtils, type Matrix4, Quaternion, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import type { QuatXYZW } from "../../../src/studio/api/types";
import {
  canonicalQuat,
  flipPose,
  matrixPose,
  poseMatrix,
  quatToYpr,
  yprToQuat,
} from "../../../src/studio/editor/pose";

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

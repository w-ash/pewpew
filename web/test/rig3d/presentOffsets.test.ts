import { describe, expect, it } from "vitest";
import { Matrix4, Vector3 } from "three";
import type { Placed } from "../../src/arrange/arrangement";
import type { Arrangement, Group } from "../../src/arrange/types";
import { matrixPose } from "../../src/arrange/pose";
import { heldPose, presentOffsets } from "../../src/rig3d/dragPreview";

/** A free fixture as the engine compiled it, at `matrix`. */
const placed = (id: string, matrix: readonly number[], group: string | null = null): Placed => ({
  id, type_id: "bar", base_type_id: "bar", group, matrix, tags: [], dims: {}, attachments: {},
});

const arrangement = (fixtures: Arrangement["fixtures"], groups: Group[] = []): Arrangement => ({
  format: "pewpew.arrangement", version: 1, fixtures, groups,
});

/** Matrices the engine compiled for aimed poses (src/pewpew/rig/pose.py `aim`, `compose`). */
const AIMED = [
  { aim: { axis: [-1, 0, 0] }, position_m: [4, 0, -2.8], matrix: [0, 0, -1, 0, -1, 0, 0, 0, 0, 1, 0, 0, 4, 0, -2.8, 1] },
  {
    aim: { axis: [0, 1, 0], roll_deg: 30 }, position_m: [0, 1, 0],
    matrix: [0.866025404, 0, -0.5, 0, 0, 1, 0, 0, 0.5, 0, 0.866025404, 0, 0, 1, 0, 1],
  },
  {
    aim: { axis: [1, 2, 3], roll_deg: -45 }, position_m: [0.5, -1, 2],
    matrix: [
      -0.790343254, 0.597614305, -0.134961785, 0, 0.267261242, 0.534522484, 0.801783726, 0, 0.551297532, 0.597614305,
      -0.582175381, 0, 0.5, -1, 2, 1,
    ],
  },
] as const;

const at = (fixture: Placed, offset: Matrix4 | undefined) => {
  const m = new Matrix4().fromArray(fixture.matrix);
  if (offset) m.premultiply(offset);
  return new Vector3().setFromMatrixPosition(m).toArray().map((v) => Math.round(v * 1e6) / 1e6);
};

describe("the editor's poses over the engine's compile", () => {
  it("moves nothing where the editor holds what the engine compiled, an aimed pose included", () => {
    const fixtures = AIMED.map((a, i) => placed(`f${i}`, a.matrix));
    const present = arrangement(
      AIMED.map((a, i) => ({ id: `f${i}`, type: "bar", pose: { position_m: [...a.position_m], aim: a.aim } as never })),
    );
    expect(presentOffsets(fixtures, present, present).size).toBe(0);
    // The gizmo's pose of an aimed fixture, made without the engine's compile.
    AIMED.forEach((a, i) => {
      const held = heldPose(present, { kind: "fixture", id: `f${i}` })!;
      const engine = matrixPose(a.matrix);
      held.quat_xyzw.forEach((v, k) => expect(v).toBeCloseTo(engine.quat_xyzw[k]!, 6));
      expect(held.position_m).toEqual(engine.position_m);
    });
    expect(heldPose(present, { kind: "group", id: "f0" })).toBeNull();
  });

  it("moves a free fixture from its compiled matrix to its pose in the editor", () => {
    const f = placed("f", AIMED[0].matrix);
    const present = arrangement([{ id: "f", type: "bar", pose: { position_m: [1, 2, 3], quat_xyzw: [0, 0, 0, 1] } }]);
    const offsets = presentOffsets([f], present, null);
    expect(at(f, offsets.get(0))).toEqual([1, 2, 3]);
    // A fixture the editor no longer holds stays where the engine drew it.
    expect(presentOffsets([f], arrangement([]), null).size).toBe(0);
  });

  it("moves a group's members by the group's move, while its members sit alike", () => {
    const ring = (x: number, count = 2): Group => ({
      id: "g", preset: "ring", type: "bar", count, start_radius_m: 1, pose: { position_m: [x, 0, 0] },
    });
    const members = [placed("g/0", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2, 0, 0, 1], "g")];
    const offsets = presentOffsets(members, arrangement([], [ring(5)]), arrangement([], [ring(1)]));
    expect(at(members[0]!, offsets.get(0))).toEqual([6, 0, 0]);
    // A group whose members moved within it (its count changed) waits for the engine's compile.
    expect(presentOffsets(members, arrangement([], [ring(5, 3)]), arrangement([], [ring(1)])).size).toBe(0);
  });
});

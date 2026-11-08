import { BoxGeometry, CylinderGeometry, Matrix4 } from "three";
import { describe, expect, it } from "vitest";
import type { Assembly } from "../../src/rig3d/assembly";
import { buildBatches, type ViewRig } from "../../src/rig3d/instances";
import { glowPoints, lightWidth, placePoints } from "../../src/rig3d/ledGlow";

const strip: Assembly = {
  parts: [
    { name: "tape", geometry: new BoxGeometry(0.01, 1, 0.002), glow: "none", gain: 1 },
    { name: "leds", geometry: new BoxGeometry(0.005, 0.99, 0.0016), glow: "pixel_nearest", gain: 1 },
  ],
  pixelAxis: { y0: -0.5, span: 1, count: 4 },
  anchors: {},
};
const tube: Assembly = {
  parts: [{ name: "tube", geometry: new CylinderGeometry(0.02, 0.02, 1.46), glow: "pixels", gain: 1 }],
  pixelAxis: { y0: -0.73, span: 1.46, count: 2 },
  anchors: {},
};
const at = (x: number) => new Matrix4().makeTranslation(x, 0, 0).elements;
const rig: ViewRig = {
  n: 6,
  fixtures: [
    { id: "a", type_id: "tube", matrix: at(5), pixel_start: 0, pixel_count: 2 },
    { id: "b", type_id: "strip", matrix: at(0), pixel_start: 2, pixel_count: 4 },
  ],
};
const assemblies = new Map([["strip", strip], ["tube", tube]]);

describe("glowPoints", () => {
  const batches = buildBatches(rig, assemblies);
  const points = glowPoints(batches, assemblies);

  it("puts one point on the axis at each pixel's centre, colored from its own texel", () => {
    expect(points.count).toBe(6);
    expect([...points.world.subarray(0, 6)].map((v) => +v.toFixed(4))).toEqual([5, -0.365, 0, 5, 0.365, 0]);
    expect([...points.world.subarray(6, 9)]).toEqual([0, -0.375, 0]);
    expect([...points.texel.subarray(0, 4)]).toEqual([0, 0, 1, 0]);
    expect([...points.texel.subarray(4, 12)]).toEqual([0, 1, 1, 1, 2, 1, 3, 1]);
    expect([...points.fixture]).toEqual([0, 0, 1, 1, 1, 1]);
  });

  it("takes each type's light width from its glowing parts", () => {
    expect(lightWidth(strip)).toBeCloseTo(0.005, 6);
    expect(lightWidth(tube)).toBeCloseTo(0.04, 6);
    expect(points.width[0]).toBeCloseTo(0.04, 6);
    expect(points.width[2]).toBeCloseTo(0.005, 6);
  });

  it("moves the points of dragged fixtures by the drag's delta", () => {
    placePoints(points, batches, new Matrix4().makeTranslation(0, 0, 2), new Set([1]));
    expect(points.world[2]).toBe(0);
    expect(points.world[8]).toBe(2);
    placePoints(points, batches, null, new Set());
    expect(points.world[8]).toBe(0);
  });
});

import { BoxGeometry, Matrix4, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { mockCatalog } from "../../../src/studio/mocks/catalog";
import { threeBarRig } from "../../../src/studio/mocks/rig";
import type { Assembly } from "../../../src/studio/viewer/assembly";
import {
  anchorMatrix,
  assembliesFor,
  buildBatches,
  hostAxis,
  missingAssemblies,
} from "../../../src/studio/viewer/instances";

const bar: Assembly = {
  parts: [
    {
      name: "diffuser",
      geometry: new BoxGeometry(0.03, 1, 0.03),
      glow: "pixels",
      gain: 1,
    },
  ],
  pixelAxis: { y0: -0.5, span: 1, count: 64 },
  anchors: {},
};
const tip: Assembly = {
  parts: [
    {
      name: "cone",
      geometry: new BoxGeometry(0.03, 0.1, 0.03),
      glow: "pixels",
      gain: 0.25,
    },
  ],
  pixelAxis: null,
  anchors: {},
};
const assemblies = new Map([
  ["clen-rgbw-bar-1m", bar],
  ["point-v0", tip],
  ["eye-v0", tip],
]);

describe("assembliesFor", () => {
  it("lists each GLB a rig needs once, fixture types first", () => {
    expect(assembliesFor(threeBarRig, mockCatalog).map((r) => r.id)).toEqual([
      "clen-rgbw-bar-1m",
      "point-v0",
      "eye-v0",
    ]);
    expect(missingAssemblies(threeBarRig, mockCatalog)).toEqual([]);
  });

  it("leaves out a type the server has no assembly for, and names it", () => {
    const catalog = {
      ...mockCatalog,
      attachment_types: mockCatalog.attachment_types.map((a) =>
        a.id === "eye-v0" ? { ...a, digest: null, assembly_url: null } : a,
      ),
    };
    expect(assembliesFor(threeBarRig, catalog).map((r) => r.id)).toEqual([
      "clen-rgbw-bar-1m",
      "point-v0",
    ]);
    expect(missingAssemblies(threeBarRig, catalog)).toEqual(["eye-v0"]);
  });
});

describe("buildBatches", () => {
  const batches = buildBatches(threeBarRig, assemblies);
  const byId = Object.fromEntries(batches.map((b) => [b.id, b]));

  it("instances every bar with the server's matrices and its own texture row", () => {
    const b = byId["clen-rgbw-bar-1m"]!;
    expect(b.count).toBe(3);
    expect([...b.rows]).toEqual([0, 1, 2]);
    expect([...b.matrices.subarray(16, 32)]).toEqual([
      ...Float32Array.from(threeBarRig.fixtures[1]!.matrix),
    ]);
    expect([...b.axisY.subarray(0, 4)]).toEqual([0, 1, 0, 0]);
    expect([...b.axis.subarray(0, 3)]).toEqual([-0.5, 1, 64]);
  });

  it("puts an end piece on the server's frame, colored by the end pixel it sits on", () => {
    const point = byId["point-v0"]!;
    expect(point.count).toBe(1);
    expect(point.rows[0]).toBe(1);
    // end_a takes pixel 0, whose center is at y0 + 0.5·span/64, for every vertex.
    expect([...point.axisY]).toEqual([0, 0, 0, -0.5 + 0.5 / 64]);
    const tipWorld = new Vector3(0, 0.1, 0).applyMatrix4(
      new Matrix4().fromArray(point.matrices),
    );
    // The host's local -Y is world +x (Rz 90°), and its middle sits at (0, 1.2, 0).
    expect(tipWorld.x).toBeCloseTo(0.6);
    expect(tipWorld.y).toBeCloseTo(1.2);
    // The eye has no server frame, so it falls back to the end of the pixel axis.
    const eye = byId["eye-v0"]!;
    // end_b takes pixel 63.
    expect([...eye.axisY]).toEqual([0, 0, 0, 0.5 - 0.5 / 64]);
    const eyeTip = new Vector3(0, 0.1, 0).applyMatrix4(
      new Matrix4().fromArray(eye.matrices),
    );
    expect(eyeTip.x).toBeCloseTo(-0.6);
    expect(eyeTip.y).toBeCloseTo(1.2);
  });

  it("skips fixtures whose GLB is not loaded", () => {
    expect(buildBatches(threeBarRig, new Map())).toEqual([]);
  });
});

describe("anchors", () => {
  it("prefers a given anchor and turns a downward one half a turn", () => {
    const axis = { y0: -0.5, span: 1, count: 64 };
    const m = anchorMatrix(
      "end_b",
      { at: [0, 0.75, 0], dir: [0, -1, 0] },
      axis,
    );
    expect(
      new Vector3(0, 1, 0)
        .applyMatrix4(m)
        .toArray()
        .map((v) => Math.round(v * 1e9) / 1e9),
    ).toEqual([0, -0.25, 0]);
  });

  it("falls back to the glowing parts' extent when the GLB has no pixel axis", () => {
    const axis = hostAxis(tip, 10);
    expect(axis.y0).toBeCloseTo(-0.05);
    expect(axis.span).toBeCloseTo(0.1);
    expect(axis.count).toBe(10);
  });
});

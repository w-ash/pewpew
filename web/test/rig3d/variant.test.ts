import { BoxGeometry, type BufferGeometry } from "three";
import { describe, expect, it } from "vitest";
import type { Assembly } from "../../src/rig3d/assembly";
import { buildBatches, type ViewRig } from "../../src/rig3d/instances";
import { drawnAssemblies } from "../../src/rig3d/Rig";
import { partsCatalog } from "../studio/fixtures/rig";

/** The y extent of a geometry. */
function yExtent(g: BufferGeometry): [number, number] {
  g.computeBoundingBox();
  return [g.boundingBox!.min.y, g.boundingBox!.max.y];
}

// The strip type's GLB at its default dims: a 1 m tape and 60 LEDs along it (one box stands in for them).
const strip: Assembly = {
  parts: [
    { name: "tape", geometry: new BoxGeometry(0.01, 1, 0.002), glow: "none", gain: 1 },
    { name: "leds", geometry: new BoxGeometry(0.005, 0.99, 0.0016).translate(0, 0, 0.001), glow: "pixel_nearest", gain: 1 },
  ],
  pixelAxis: { y0: -0.5, span: 1, count: 60 },
  anchors: { end_a: { at: [0, -0.5, 0], dir: [0, -1, 0] }, end_b: { at: [0, 0.5, 0], dir: [0, 1, 0] } },
};
const catalog = {
  ...partsCatalog,
  fixture_types: [{ id: "strip", name: "Straight LED strip", digest: "d", assembly_url: "/assembly/d.glb", dims: { length: { v: 1 } } }],
};
const variant = (id: string, dims: Record<string, number>, count: number) => ({
  id, type_id: `strip.${id}`, base_type_id: "strip", dims, pixel_start: 0, pixel_count: count,
  matrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
});

describe("drawnAssemblies", () => {
  const long = variant("long", { pixels: 64, length: 2, pitch: 2 / 64 }, 64);
  const rig: ViewRig = { n: 64, fixtures: [long], types: { "strip.long": { count: 64, span_m: 2 } } };
  const drawn = drawnAssemblies(rig, catalog, new Map([["strip", strip]]));

  it("draws a variant from its base type, by its own id, never by fetching it", () => {
    expect([...drawn.keys()]).toEqual(["strip", "strip.long"]);
    expect(buildBatches(rig, drawn).map((b) => b.id)).toEqual(["strip.long"]);
  });

  it("makes its pixels one bar over its span, and stretches the rest to its length", () => {
    const a = drawn.get("strip.long")!;
    expect(a.pixelAxis).toEqual({ y0: -1, span: 2, count: 64 });
    expect(yExtent(a.parts[0]!.geometry)).toEqual([-1, 1]);
    expect(yExtent(a.parts[1]!.geometry)).toEqual([-1, 1]);
    expect(a.parts[1]!.glow).toBe("pixel_nearest");
    expect(a.anchors.end_a?.at).toEqual([0, -1, 0]);
    // The base type's own geometry is left as it was.
    expect(yExtent(strip.parts[0]!.geometry)).toEqual([-0.5, 0.5]);
  });

  it("takes the span from the pitch, and the stretch from the span, on a rig without types or length", () => {
    const short = variant("short", { pixels: 30, pitch: 0.01 }, 30);
    const a = drawnAssemblies({ n: 30, fixtures: [short] }, catalog, new Map([["strip", strip]])).get("strip.short")!;
    expect(a.pixelAxis?.span).toBeCloseTo(0.3);
    const [lo, hi] = yExtent(a.parts[0]!.geometry);
    expect(hi - lo).toBeCloseTo(0.3);
  });
});

import { BoxGeometry, type BufferGeometry, CylinderGeometry } from "three";
import { describe, expect, it } from "vitest";
import type { Assembly } from "../../src/rig3d/assembly";
import { buildBatches, type ViewRig } from "../../src/rig3d/instances";
import { assembliesKey, drawnAssemblies } from "../../src/rig3d/Rig";
import { partsCatalog } from "../studio/fixtures/rig";

/** The y extent of a geometry. */
function yExtent(g: BufferGeometry): [number, number] {
  g.computeBoundingBox();
  return [g.boundingBox!.min.y, g.boundingBox!.max.y];
}

/** The x extent of a geometry. */
function width(g: BufferGeometry): number {
  g.computeBoundingBox();
  return g.boundingBox!.max.x - g.boundingBox!.min.x;
}

function expectExtent(g: BufferGeometry | undefined, lo: number, hi: number) {
  const [a, b] = yExtent(g!);
  expect(a).toBeCloseTo(lo, 6);
  expect(b).toBeCloseTo(hi, 6);
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

// The tube type's GLB at its default dims: a 1.46 m opal tube between two 20 mm caps, 1.5 m in all.
const tube: Assembly = {
  parts: [
    { name: "tube", geometry: new CylinderGeometry(0.02, 0.02, 1.46), glow: "pixels", gain: 1 },
    { name: "cap_a", geometry: new CylinderGeometry(0.021, 0.021, 0.02).translate(0, -0.74, 0), glow: "none", gain: 1 },
    { name: "cap_b", geometry: new CylinderGeometry(0.021, 0.021, 0.02).translate(0, 0.74, 0), glow: "none", gain: 1 },
  ],
  pixelAxis: { y0: -0.73, span: 1.46, count: 36 },
  anchors: {},
};

// The bar type's GLB at its default dims: a 1 m housing between 4 mm caps, its strip and LEDs, and the
// diffuser over the whole length.
const bar: Assembly = {
  parts: [
    { name: "housing", geometry: new BoxGeometry(0.018, 0.992, 0.0185), glow: "none", gain: 1 },
    { name: "cap_a", geometry: new BoxGeometry(0.018, 0.004, 0.0185).translate(0, -0.498, 0), glow: "none", gain: 1 },
    { name: "cap_b", geometry: new BoxGeometry(0.018, 0.004, 0.0185).translate(0, 0.498, 0), glow: "none", gain: 1 },
    { name: "strip", geometry: new BoxGeometry(0.01, 1, 0.001), glow: "none", gain: 1 },
    { name: "leds", geometry: new BoxGeometry(0.005, 0.99, 0.0016), glow: "pixel_nearest", gain: 1 },
    { name: "diffuser", geometry: new CylinderGeometry(0.0151, 0.0151, 1), glow: "pixels", gain: 1 },
  ],
  pixelAxis: { y0: -0.5, span: 1, count: 64 },
  anchors: {},
};

describe("variantAssembly, through drawnAssemblies", () => {
  const types = {
    ...partsCatalog,
    fixture_types: [
      { id: "tube", name: "Tube", digest: "t", assembly_url: "/assembly/t.glb", dims: { length: { v: 1.5 } } },
      { id: "bar", name: "Bar", digest: "b", assembly_url: "/assembly/b.glb", dims: { length: { v: 1 } } },
    ],
  };
  const loaded = new Map([["tube", tube], ["bar", bar]]);
  const of = (base: string, id: string, dims: Record<string, number>, count: number, span: number) => {
    const f = { ...variant(id, dims, count), type_id: `${base}.${id}`, base_type_id: base };
    const rig: ViewRig = { n: count, fixtures: [f], types: { [f.type_id]: { count, span_m: span } } };
    return drawnAssemblies(rig, types, loaded).get(f.type_id)!;
  };
  const part = (a: Assembly, name: string) => a.parts.find((p) => p.name === name)?.geometry;

  it("draws a shorter tube round, its tube over the span and its caps at their size on the new ends", () => {
    const a = of("tube", "short", { length: 1 }, 24, 0.96);
    expectExtent(part(a, "tube"), -0.48, 0.48);
    expectExtent(part(a, "cap_a"), -0.5, -0.48);
    expectExtent(part(a, "cap_b"), 0.48, 0.5);
    // Still a cylinder, not a box: the same vertices as the base type's, only moved along y.
    expect(part(a, "tube")!.getAttribute("position").count).toBe(tube.parts[0]!.geometry.getAttribute("position").count);
    expect(width(part(a, "tube")!)).toBeCloseTo(0.04, 6);
  });

  it("draws a longer bar: housing and strip stretched, caps moved, LEDs one bar, the diffuser over the span", () => {
    const a = of("bar", "long", { length: 2 }, 128, 2);
    expectExtent(part(a, "housing"), -0.992, 0.992);
    expectExtent(part(a, "cap_a"), -1, -0.996);
    expectExtent(part(a, "cap_b"), 0.996, 1);
    expectExtent(part(a, "strip"), -1, 1);
    expectExtent(part(a, "leds"), -1, 1);
    expectExtent(part(a, "diffuser"), -1, 1);
    expect(part(a, "diffuser")!.getAttribute("position").count).toBe(bar.parts[5]!.geometry.getAttribute("position").count);
  });

  it("does not draw a dim of the cross-section: a wider housing draws at the base type's width", () => {
    const a = of("bar", "wide", { length: 1, housing_w: 0.03 }, 64, 1);
    expect(width(part(a, "housing")!)).toBeCloseTo(0.018, 6);
    expectExtent(part(a, "housing"), -0.496, 0.496);
    expectExtent(part(a, "cap_b"), 0.496, 0.5);
    expectExtent(part(a, "diffuser"), -0.5, 0.5);
  });
});

describe("assembliesKey", () => {
  const at = (x: number) => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, 0, 0, 1];
  const rig = (fixtures: ViewRig["fixtures"]): ViewRig => ({ n: 128, fixtures });
  const a = { ...variant("a", { length: 2, pixels: 64 }, 64), matrix: at(0) };
  const b = { ...variant("b", { length: 1, pixels: 64 }, 64), pixel_start: 64, matrix: at(1) };

  it("is the same for a rig whose fixtures only moved, so their assemblies are kept", () => {
    const moved = rig([{ ...b, matrix: at(5) }, { ...a, id: "a2", matrix: at(-3), dims: { pixels: 64, length: 2 } }]);
    expect(assembliesKey(moved)).toBe(assembliesKey(rig([a, b])));
  });

  it("changes with a type's dims, pixels or span", () => {
    const key = assembliesKey(rig([a, b]));
    expect(assembliesKey(rig([a, { ...b, dims: { length: 1.5, pixels: 64 } }]))).not.toBe(key);
    expect(assembliesKey(rig([a, { ...b, pixel_count: 60 }]))).not.toBe(key);
    expect(assembliesKey({ ...rig([a, b]), types: { "strip.b": { count: 64, span_m: 0.9 } } })).not.toBe(key);
  });
});

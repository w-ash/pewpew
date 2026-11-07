import { describe, expect, test } from "vitest";
import { decodeParam, defOf, equalValue, formatValue, readValue } from "../../src/domain/params/kinds";
import type { Gradient, PaletteParam, Param, Stop } from "../../src/domain/params/schema";
import { param, record } from "../fixtures/describe";

const stop = (at: number, h = 0, s = 1, v = 1): Stop => ({ at, h, s, v });

describe("decode", () => {
  test.each([
    ["colorplasma", "speed", "float"],
    ["zoo", "bands", "int"],
    ["zoo", "invert", "bool"],
    ["zoo", "shape", "choice"],
    ["colorplasma", "color_a", "color"],
    ["zoo", "palette", "palette"],
  ])("%s.%s is a %s", (pattern, name, kind) => {
    expect(param(pattern, name).kind).toBe(kind);
  });

  test("keeps the meta fields", () => {
    const p = param("wave", "direction");
    expect(p).toMatchObject({ label: "Direction", widget: "angle", group: "", periodic: true, unit: "°" });
    expect(param("colorplasma", "cycle_a")).toMatchObject({ group: "Low", text: [{ value: 0, label: "hold" }] });
  });

  test.each<[string, Record<string, unknown>]>([
    ["an unknown kind", { kind: "point2d" }],
    ["no kind", { kind: undefined }],
    ["lo not below hi", { lo: 1, hi: 1 }],
    ["a non-numeric step", { step: "x" }],
    ["a default of the wrong type", { default: "fast" }],
    ["a malformed text label", { text: [{ value: "0", label: "hold" }] }],
  ])("a float with %s is unknown", (_why, patch) => {
    const p = decodeParam({ ...record("colorplasma", "speed"), ...patch });
    expect(p.kind).toBe("unknown");
    expect(p.name).toBe("speed");
  });

  test("an int with a fractional range is unknown", () => {
    expect(decodeParam({ ...record("zoo", "bands"), lo: 0.5 }).kind).toBe("unknown");
  });

  test("a choice whose default is not an option is unknown", () => {
    expect(decodeParam({ ...record("zoo", "shape"), default: "nope" }).kind).toBe("unknown");
  });

  test("a color without all three parts is unknown", () => {
    const r = record("colorplasma", "color_a");
    const { v: _, ...parts } = r.parts as Record<string, unknown>;
    expect(decodeParam({ ...r, parts }).kind).toBe("unknown");
  });

  test("a palette keeps its stop parts, its cap and its presets", () => {
    const p = param("zoo", "palette") as PaletteParam;
    expect(p.stop.at).toMatchObject({ label: "Position", lo: 0, hi: 1 });
    expect(p.stop.h).toMatchObject({ label: "Hue", periodic: true, unit: "°" });
    expect(p.maxStops).toBe(16);
    expect(p.presets.map((x) => x.label)).toEqual(["ember", "ocean", "aurora", "synthwave", "forest", "ice", "candy", "mono"]);
    expect(p.presets[0]!.value).toEqual(p.default);
  });

  test.each<[string, (r: Record<string, unknown>) => Record<string, unknown>]>([
    ["no stop parts", ({ stop: _, ...r }) => r],
    ["a stop part missing", (r) => ({ ...r, stop: { ...(r.stop as object), v: undefined } })],
    ["a cap below 2", (r) => ({ ...r, max_stops: 1 })],
    ["a malformed preset", (r) => ({ ...r, presets: [{ label: "x", value: { stops: [] } }] })],
    ["a default out of order", (r) => ({ ...r, default: { label: "", stops: [stop(0), stop(0.6), stop(0.5), stop(1)] } })],
  ])("a palette with %s is unknown", (_why, patch) => {
    expect(decodeParam(patch(record("zoo", "palette"))).kind).toBe("unknown");
  });

  test("a record that is not an object is unknown", () => {
    expect(decodeParam(42)).toMatchObject({ kind: "unknown", name: "" });
  });
});

describe("read and equal", () => {
  const cases: [Param, unknown, unknown, unknown][] = [
    [param("colorplasma", "speed"), 0.25, true, "0.25"],
    [param("zoo", "bands"), 4, 4.5, true],
    [param("zoo", "invert"), true, 1, "true"],
    [param("zoo", "shape"), "steps", "nope", 1],
    [param("colorplasma", "color_a"), { h: 10, s: 0.5, v: 1 }, { h: 10, s: 0.5 }, [10, 0.5, 1]],
    [
      param("zoo", "palette"),
      { label: "", stops: [stop(0), stop(1)] },
      { stops: [stop(0)] },
      { stops: [stop(0.5), stop(1)] },
    ],
  ];
  test.each(cases)("%# reads its own values and refuses others", (p, good, ...bad) => {
    expect(readValue(p, good)).toEqual(good);
    for (const b of bad) expect(readValue(p, b)).toBeUndefined();
  });

  test("a palette's label may be left out, and reads as none", () => {
    expect(readValue(param("zoo", "palette"), { stops: [stop(0), stop(1)] })).toEqual({ label: "", stops: [stop(0), stop(1)] });
  });

  test("palette equality is per stop and label", () => {
    const p = param("zoo", "palette");
    const g: Gradient = { label: "", stops: [stop(0), stop(1)] };
    expect(equalValue(p, g, { label: "", stops: [stop(0), stop(1)] })).toBe(true);
    expect(equalValue(p, g, { label: "x", stops: [stop(0), stop(1)] })).toBe(false);
    expect(equalValue(p, g, { label: "", stops: [stop(0), stop(1, 10)] })).toBe(false);
  });

  test("color equality is per part", () => {
    const p = param("colorplasma", "color_a");
    expect(equalValue(p, { h: 1, s: 1, v: 1 }, { h: 1, s: 1, v: 1 })).toBe(true);
    expect(equalValue(p, { h: 1, s: 1, v: 1 }, { h: 1, s: 1, v: 0.5 })).toBe(false);
  });
});

describe("format", () => {
  test("a float reads at its decimals with its unit", () => {
    expect(formatValue(param("colorplasma", "speed"), 0.5)).toBe("0.50 /s");
    expect(formatValue(param("colorplasma", "scale"), 4)).toBe("4.00");
  });
  test("a text label overrides the number at the shown precision", () => {
    const p = param("colorplasma", "cycle_a");
    expect(formatValue(p, 0)).toBe("hold");
    expect(formatValue(p, 0.01)).toBe("hold");
    expect(formatValue(p, 0.5)).toBe("0.5 s");
  });
  test("an angle reads in degrees", () => {
    expect(formatValue(param("wave", "direction"), 90)).toBe("90°");
  });
  test("int, bool, choice and color", () => {
    expect(formatValue(param("zoo", "bands"), 5)).toBe("5");
    expect(formatValue(param("zoo", "invert"), true)).toBe("on");
    expect(formatValue(param("zoo", "shape"), "steps")).toBe("Steps");
    expect(formatValue(param("colorplasma", "color_a"), { h: 126, s: 1, v: 0.5 })).toBe("126° · 100% · 50%");
  });
  test("a palette reads as its label, or its stop count", () => {
    const p = param("zoo", "palette");
    expect(formatValue(p, (p as PaletteParam).default)).toBe("ember");
    expect(formatValue(p, { label: "", stops: [stop(0), stop(0.5), stop(1)] })).toBe("3 stops");
  });
  test("no negative zero", () => {
    expect(formatValue(param("colorplasma", "speed"), -0.0001)).toBe("0.00 /s");
  });
});

describe("palette normalize", () => {
  const p = param("zoo", "palette") as PaletteParam;
  const norm = (g: Gradient, prev: Gradient) => defOf(p).normalize(p, g, prev);
  const prev: Gradient = { label: "", stops: [stop(0, 5), stop(0.3), stop(0.6), stop(1)] };

  test("an edit fits only what it changed; a hue between steps stays", () => {
    const next = norm({ label: "", stops: prev.stops.with(1, stop(0.3, 31, 0.5011)) }, prev);
    expect(next.stops).toEqual([stop(0, 5), stop(0.3, 32, 0.5), stop(0.6), stop(1)]);
  });

  test("a stop moved past a neighbour stops there, and the ends stay at 0 and 1", () => {
    expect(norm({ label: "", stops: prev.stops.with(1, stop(0.9)) }, prev).stops.map((s) => s.at)).toEqual([0, 0.6, 0.6, 1]);
    expect(norm({ label: "", stops: prev.stops.with(2, stop(0.1)) }, prev).stops.map((s) => s.at)).toEqual([0, 0.3, 0.3, 1]);
    expect(norm({ label: "", stops: prev.stops.slice(1) }, prev).stops.map((s) => s.at)).toEqual([0, 0.6, 1]);
  });

  test("a stop added or removed leaves the others as they were", () => {
    const added = norm({ label: "", stops: prev.stops.toSpliced(1, 0, stop(0.15, 5)) }, prev);
    expect(added.stops).toEqual([stop(0, 5), stop(0.15, 6), stop(0.3), stop(0.6), stop(1)]);
  });

  test("a preset goes as declared", () => {
    const ocean = p.presets[1]!.value;
    expect(norm(ocean, prev)).toBe(ocean);
  });
});

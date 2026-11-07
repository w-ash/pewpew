import { describe, expect, it } from "vitest";
import { MOCK_PATTERNS } from "@/mocks/frames";
import { describeGolden, zooRecord } from "@/test/describe";
import {
  decodeParam,
  decodeParams,
  decodeValues,
  gradientCss,
  hexToHsv,
  hsvToHex,
  presetOf,
  valueFor,
} from "./params";

describe("decodeParam", () => {
  it("reads every kind the engine declares", () => {
    const kinds = MOCK_PATTERNS.pulse.map((p) => decodeParam(p)?.kind);
    expect(kinds).toEqual(["color", "int", "bool", "choice"]);
    expect(decodeParam(MOCK_PATTERNS.rainbow[0])?.kind).toBe("float");
  });

  it("refuses a malformed record of a known kind, and keeps an unknown kind", () => {
    expect(decodeParam({ name: "x", kind: "float", default: 1 })).toBeNull();
    expect(
      decodeParam({
        name: "x",
        kind: "choice",
        default: "c",
        options: [{ value: "a" }],
      }),
    ).toBeNull();
    expect(decodeParam({ name: "x", kind: "bool", default: 1 })).toBeNull();
    expect(
      decodeParam({ name: "x", kind: "vector", default: [1, 2] }),
    ).toMatchObject({
      kind: "unknown",
      label: "x",
    });
    expect(decodeParams([MOCK_PATTERNS.plasma[0], { name: "x" }])).toEqual([
      expect.objectContaining({ name: "speed" }),
      expect.objectContaining({ kind: "unknown" }),
    ]);
    expect(decodeParams("nope")).toBeNull();
  });
});

describe("valueFor", () => {
  it("takes a value of the param's kind and falls back to the default", () => {
    const [color, bands, invert, shape] = MOCK_PATTERNS.pulse;
    expect(valueFor(bands, 4)).toBe(4);
    expect(valueFor(bands, "4")).toBe(2);
    expect(valueFor(invert, true)).toBe(true);
    expect(valueFor(invert, 1)).toBe(false);
    expect(valueFor(shape, "flat")).toBe("flat");
    expect(valueFor(color, { h: 1 })).toEqual({ h: 200, s: 1, v: 1 });
  });
});

describe("color", () => {
  it("shows the engine's HSV through the display gamma", () => {
    expect(hsvToHex({ h: 0, s: 1, v: 1 })).toBe("#ff0000");
    expect(hsvToHex({ h: 120, s: 0, v: 0 })).toBe("#000000");
    // Half the linear light is brighter than half on screen.
    expect(hsvToHex({ h: 0, s: 0, v: 0.5 })).toBe("#bababa");
  });

  it("turns a picked screen color back into the HSV that shows it", () => {
    expect(hexToHsv("#ff0000")).toEqual({ h: 0, s: 1, v: 1 });
    expect(hexToHsv("#0000ff")).toEqual({ h: 240, s: 1, v: 1 });
    const grey = hexToHsv("#bababa");
    expect(grey?.s).toBe(0);
    expect(grey?.v).toBeCloseTo(0.5, 3);
    expect(hexToHsv("blue")).toBeNull();
    // Every screen color comes back as itself, the dark ones too.
    const hex = (c: number[]) =>
      `#${c.map((x) => x.toString(16).padStart(2, "0")).join("")}`;
    const off: string[] = [];
    for (let r = 0; r < 256; r += 5)
      for (let g = 0; g < 256; g += 5)
        for (let b = 0; b < 256; b += 5) {
          const want = hex([r, g, b]);
          const back = hsvToHex(hexToHsv(want) ?? { h: 0, s: 0, v: 0 });
          if (back !== want) off.push(`${want} -> ${back}`);
        }
    expect(off.slice(0, 5)).toEqual([]);
  });
});

describe("the engine's records", () => {
  const patterns = describeGolden();

  it("decode, each to its own kind, with its default kept", () => {
    const kinds = new Set<string>();
    for (const [pattern, records] of Object.entries(patterns))
      for (const raw of records) {
        const spec = decodeParam(raw);
        const { name, kind, default: dflt } = raw as Record<string, unknown>;
        expect(spec, `${pattern}.${name}`).not.toBeNull();
        expect(spec?.kind, `${pattern}.${name}`).toBe(kind);
        if (spec) {
          expect(valueFor(spec, dflt)).toEqual(dflt);
          expect(decodeValues({ [spec.name]: dflt })).toEqual({
            [spec.name]: dflt,
          });
        }
        kinds.add(String(kind));
      }
    expect([...kinds].sort()).toEqual([
      "bool",
      "choice",
      "color",
      "float",
      "int",
      "palette",
    ]);
  });

  it("give a palette its stop parts and its presets", () => {
    const raw = zooRecord("palette");
    const spec = decodeParam(raw);
    if (spec?.kind !== "palette") throw new Error("no palette in the zoo");
    expect(Object.keys(spec.stop)).toEqual(["at", "h", "s", "v"]);
    expect(spec.stop.h).toMatchObject({ lo: 0, hi: 360, periodic: true });
    expect(spec.presets.map((p) => p.label)).toContain("ocean");
    const ocean = spec.presets.find((p) => p.label === "ocean")?.value;
    expect(ocean && presetOf(spec.presets, ocean)).toBe("ocean");
    expect(presetOf(spec.presets, spec.default)).toBe(spec.default.label);
    const own = {
      label: "",
      stops: [
        { at: 0, h: 0, s: 1, v: 1 },
        { at: 1, h: 240, s: 1, v: 1 },
      ],
    };
    expect(presetOf(spec.presets, own)).toBeNull();
    expect(valueFor(spec, own)).toEqual(own);
    // A gradient needs a label and two stops of {at, h, s, v}.
    expect(valueFor(spec, { stops: own.stops })).toEqual(spec.default);
    expect(valueFor(spec, { label: "", stops: own.stops.slice(1) })).toEqual(
      spec.default,
    );
    expect(gradientCss(own)).toBe(
      "linear-gradient(to right, #ff0000 0%, #0000ff 100%)",
    );
  });

  it("refuse a palette record without its stop parts", () => {
    const raw = zooRecord("palette");
    expect(decodeParam({ ...raw, stop: { at: raw.stop } })).toBeNull();
    expect(decodeParam({ ...raw, default: "ember" })).toBeNull();
  });
});

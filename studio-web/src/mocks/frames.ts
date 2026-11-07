/**
 * Fake engine output for the mock session: display-ready RGB frames from
 * three toy patterns. Nothing here resembles pewpew's real patterns beyond
 * the param records (`Param.spec()`, src/pewpew/params/kinds.py); `pulse`
 * declares one param of every other kind.
 */
import type { Hsv, ParamSpec, ParamValue } from "@/api/types";
import { DISPLAY_GAMMA, linearRgb } from "@/session/params";
import { MOCK_PIXELS_PER_BAR } from "./catalog";

const common = { help: "", group: "", widget: "" };

function float(
  name: string,
  label: string,
  def: number,
  hi: number,
  unit = "",
): ParamSpec {
  return {
    ...common,
    kind: "float",
    name,
    label,
    default: def,
    lo: 0,
    hi,
    step: 0.01,
    decimals: 2,
    unit,
    periodic: false,
  };
}

const part = (
  label: string,
  hi: number,
  step: number,
  decimals: number,
  unit = "",
) => ({
  label,
  lo: 0,
  hi,
  step,
  decimals,
  unit,
  periodic: hi === 360,
});

export const MOCK_PATTERNS: Record<string, ParamSpec[]> = {
  rainbow: [
    float("speed", "Speed", 0.25, 2, "/s"),
    float("spread", "Spread", 0.5, 2),
    float("level", "Level", 1, 1),
  ],
  plasma: [float("speed", "Speed", 0.5, 2, "/s")],
  pulse: [
    {
      ...common,
      kind: "color",
      name: "color",
      label: "Color",
      default: { h: 200, s: 1, v: 1 },
      parts: {
        h: part("Hue", 360, 2, 0, "°"),
        s: part("Saturation", 1, 0.005, 3),
        v: part("Brightness", 1, 0.005, 3),
      },
    },
    {
      ...common,
      kind: "int",
      name: "bands",
      label: "Bands",
      default: 2,
      lo: 1,
      hi: 6,
      step: 1,
      decimals: 0,
      unit: "",
      periodic: false,
    },
    {
      ...common,
      kind: "bool",
      name: "invert",
      label: "Invert",
      default: false,
    },
    {
      ...common,
      kind: "choice",
      name: "shape",
      label: "Shape",
      default: "ramp",
      options: [
        { value: "ramp", label: "Ramp" },
        { value: "flat", label: "Flat" },
      ],
    },
  ],
};

/** Why `value` is refused for `spec`, or null: the engine's checks, roughly. */
export function mockRefusal(spec: ParamSpec, value: unknown): string | null {
  const inRange = (x: unknown, lo: number, hi: number) =>
    typeof x === "number" && Number.isFinite(x) && x >= lo && x <= hi;
  switch (spec.kind) {
    case "float":
      return inRange(value, spec.lo, spec.hi)
        ? null
        : `${spec.name} must be within ${spec.lo}..${spec.hi}`;
    case "int":
      return Number.isInteger(value) && inRange(value, spec.lo, spec.hi)
        ? null
        : `${spec.name} takes a whole number within ${spec.lo}..${spec.hi}`;
    case "bool":
      return typeof value === "boolean"
        ? null
        : `${spec.name} takes true or false`;
    case "choice":
      return spec.options.some((o) => o.value === value)
        ? null
        : `${spec.name} takes one of the options`;
    case "color": {
      const c = value as Partial<Hsv> | null;
      const { h, s, v } = spec.parts;
      return c &&
        inRange(c.h, h.lo, h.hi) &&
        inRange(c.s, s.lo, s.hi) &&
        inRange(c.v, v.lo, v.hi)
        ? null
        : `${spec.name} takes {h, s, v} within range`;
    }
    default:
      return `${spec.name} cannot be set`;
  }
}

function hue(h: number, level: number, out: Uint8Array, at: number) {
  const k = (n: number) => (n + h * 6) % 6;
  const f = (n: number) => 1 - Math.max(0, Math.min(k(n), 4 - k(n), 1));
  out[at] = Math.round(255 * f(5) * level);
  out[at + 1] = Math.round(255 * f(3) * level);
  out[at + 2] = Math.round(255 * f(1) * level);
}

export function renderMockFrame(
  pattern: string,
  values: Record<string, ParamValue>,
  n: number,
  t: number,
): Uint8Array {
  const rgb = new Uint8Array(n * 3);
  const num = (k: string, d: number) =>
    typeof values[k] === "number" ? (values[k] as number) : d;
  const speed = num("speed", 0.25);
  if (pattern === "pulse") {
    const [r, g, b] = linearRgb(
      (values.color as Hsv | undefined) ?? { h: 200, s: 1, v: 1 },
    );
    const bands = num("bands", 2);
    for (let i = 0; i < n; i++) {
      const x = (i % MOCK_PIXELS_PER_BAR) / MOCK_PIXELS_PER_BAR;
      let k = values.shape === "flat" ? 0.5 : (x * bands) % 1;
      if (values.invert === true) k = 1 - k;
      const level = (0.2 + 0.8 * k) * (0.6 + 0.4 * Math.sin(t * 2));
      rgb[i * 3] = Math.round(255 * (r * level) ** (1 / DISPLAY_GAMMA));
      rgb[i * 3 + 1] = Math.round(255 * (g * level) ** (1 / DISPLAY_GAMMA));
      rgb[i * 3 + 2] = Math.round(255 * (b * level) ** (1 / DISPLAY_GAMMA));
    }
    return rgb;
  }
  if (pattern === "plasma") {
    for (let i = 0; i < n; i++) {
      const j = i % MOCK_PIXELS_PER_BAR;
      const bar = Math.floor(i / MOCK_PIXELS_PER_BAR);
      const v = 0.5 + 0.5 * Math.sin(j / 6 + bar * 0.7 + t * speed * 6);
      hue((v * 0.4 + 0.55) % 1, 0.25 + 0.75 * v, rgb, i * 3);
    }
    return rgb;
  }
  const spread = num("spread", 0.5);
  const level = num("level", 1);
  for (let i = 0; i < n; i++) {
    const j = i % MOCK_PIXELS_PER_BAR;
    const h = ((((j / MOCK_PIXELS_PER_BAR) * spread - t * speed) % 1) + 1) % 1;
    hue(h, level, rgb, i * 3);
  }
  return rgb;
}

/** Watts if each pixel drew 0.4 W at full white, from linear light (gamma 2.2). */
export function mockWatts(rgb: Uint8Array): number {
  let sum = 0;
  for (let i = 0; i < rgb.length; i++) sum += (rgb[i] / 255) ** 2.2;
  return (sum / 3) * 0.4;
}

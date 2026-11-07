/**
 * Param records and values as the engine sends them: each record is one
 * `Param.spec()` (src/pewpew/params/kinds.py), each value its kind's JSON
 * form (`ParamSet.snapshot_json()`). The engine parses every value it gets,
 * so this module only decides what a control can show and send.
 */
import type {
  Gradient,
  Hsv,
  NumberSpec,
  ParamSpec,
  ParamValue,
} from "@/api/types";

/** `DISPLAY_GAMMA` in src/pewpew/sinks/base.py: linear light to screen. */
export const DISPLAY_GAMMA = 2.2;

type Raw = Record<string, unknown>;

export const isNum = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);
export const isStr = (v: unknown): v is string => typeof v === "string";
export const isObj = (v: unknown): v is Raw =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): string => (isStr(v) ? v : "");

function isHsv(v: unknown): v is Hsv {
  return isObj(v) && isNum(v.h) && isNum(v.s) && isNum(v.v);
}

/** A palette's JSON form: a label and at least 2 stops, each `{at, h, s, v}`.
 * The engine checks the order and the ends. */
function isGradient(v: unknown): v is Gradient {
  return (
    isObj(v) &&
    isStr(v.label) &&
    Array.isArray(v.stops) &&
    v.stops.length >= 2 &&
    v.stops.every((stop) => isObj(stop) && isNum(stop.at) && isHsv(stop))
  );
}

function isParamValue(v: unknown): v is ParamValue {
  return (
    isNum(v) || typeof v === "boolean" || isStr(v) || isHsv(v) || isGradient(v)
  );
}

/** The labeled numeric records of a compound value's parts, or null when
 * any of `keys` is missing or malformed. */
function partSpecs<K extends string>(
  raw: unknown,
  keys: readonly K[],
): Record<K, NumberSpec & { label: string }> | null {
  if (!isObj(raw)) return null;
  const out = {} as Record<K, NumberSpec & { label: string }>;
  for (const k of keys) {
    const p = raw[k];
    const n = isObj(p) ? numberSpec(p) : null;
    if (!isObj(p) || !n) return null;
    out[k] = { ...n, label: text(p.label) || k };
  }
  return out;
}

function numberSpec(raw: Raw): NumberSpec | null {
  const { lo, hi, step, decimals } = raw;
  if (!isNum(lo) || !isNum(hi) || !(lo <= hi)) return null;
  if (!isNum(step) || step <= 0) return null;
  return {
    lo,
    hi,
    step,
    decimals: isNum(decimals) && decimals >= 0 ? decimals : 2,
    unit: text(raw.unit),
    periodic: raw.periodic === true,
  };
}

/** One record, or null when a known kind's record is malformed. A kind
 * this page does not know is kept as `unknown`, so the panel still lists it. */
export function decodeParam(raw: unknown): ParamSpec | null {
  if (!isObj(raw) || !isStr(raw.name) || !raw.name) return null;
  const common = {
    name: raw.name,
    label: text(raw.label) || raw.name,
    help: text(raw.help),
    group: text(raw.group),
    widget: text(raw.widget),
  };
  switch (raw.kind) {
    case "float":
    case "int": {
      const n = numberSpec(raw);
      if (!n || !isNum(raw.default)) return null;
      return { ...common, ...n, kind: raw.kind, default: raw.default };
    }
    case "bool":
      if (typeof raw.default !== "boolean") return null;
      return { ...common, kind: "bool", default: raw.default };
    case "choice": {
      if (!isStr(raw.default) || !Array.isArray(raw.options)) return null;
      const options = raw.options
        .filter((o): o is Raw => isObj(o) && isStr(o.value))
        .map((o) => ({
          value: o.value as string,
          label: text(o.label) || (o.value as string),
        }));
      if (!options.some((o) => o.value === raw.default)) return null;
      return { ...common, kind: "choice", default: raw.default, options };
    }
    case "color": {
      const parts = partSpecs(raw.parts, ["h", "s", "v"] as const);
      if (!isHsv(raw.default) || !parts) return null;
      return { ...common, kind: "color", default: raw.default, parts };
    }
    case "palette": {
      const stop = partSpecs(raw.stop, ["at", "h", "s", "v"] as const);
      if (!isGradient(raw.default) || !stop || !Array.isArray(raw.presets))
        return null;
      const presets = raw.presets
        .filter(
          (p): p is Raw => isObj(p) && isStr(p.label) && isGradient(p.value),
        )
        .map((p) => ({ value: p.value as Gradient, label: p.label as string }));
      return {
        ...common,
        kind: "palette",
        default: raw.default,
        stop,
        max_stops: isNum(raw.max_stops) ? raw.max_stops : 16,
        presets,
      };
    }
    default:
      return { ...common, kind: "unknown", default: raw.default };
  }
}

/** Every record, or null when any is malformed. */
export function decodeParams(v: unknown): ParamSpec[] | null {
  if (!Array.isArray(v)) return null;
  const out: ParamSpec[] = [];
  for (const raw of v) {
    const p = decodeParam(raw);
    if (!p) return null;
    out.push(p);
  }
  return out;
}

/** The values of a `values` object that a control could hold. */
export function decodeValues(v: unknown): Record<string, ParamValue> {
  const out: Record<string, ParamValue> = {};
  if (isObj(v))
    for (const [k, x] of Object.entries(v)) if (isParamValue(x)) out[k] = x;
  return out;
}

/** `value` when it fits `spec`'s kind, else the default. */
export function valueFor<P extends ParamSpec>(
  spec: P,
  value: unknown,
): P["default"] {
  switch (spec.kind) {
    case "float":
    case "int":
      return isNum(value) ? value : spec.default;
    case "bool":
      return typeof value === "boolean" ? value : spec.default;
    case "choice":
      return isStr(value) ? value : spec.default;
    case "color":
      return isHsv(value) ? value : spec.default;
    case "palette":
      return isGradient(value) ? value : spec.default;
    default:
      return value ?? spec.default;
  }
}

/** Linear-light RGB in 0..1 for `hsv`, as `pewpew.kit.hsv` computes it. */
export function linearRgb({ h, s, v }: Hsv): [number, number, number] {
  const h6 = ((((h / 360) % 1) + 1) % 1) * 6;
  const chan = (n: number) => {
    const k = (n + h6) % 6;
    return v - v * s * Math.min(Math.max(Math.min(k, 4 - k), 0), 1);
  };
  return [chan(5), chan(3), chan(1)];
}

const hex2 = (c: number) =>
  Math.round(255 * Math.min(Math.max(c, 0), 1) ** (1 / DISPLAY_GAMMA))
    .toString(16)
    .padStart(2, "0");

/** `#rrggbb` as the screen shows `hsv`: display gamma over the linear light. */
export function hsvToHex(hsv: Hsv): string {
  return `#${linearRgb(hsv).map(hex2).join("")}`;
}

/** A CSS gradient through each stop's screen color. The engine blends in
 * OKLab, so the swatch between stops is close, not exact. */
export function gradientCss(g: Gradient): string {
  const stops = g.stops.map((s) => `${hsvToHex(s)} ${s.at * 100}%`);
  return `linear-gradient(to right, ${stops.join(", ")})`;
}

/** The preset that `value` is, by label and stops, or null for a gradient
 * of the visitor's own. */
export function presetOf(
  presets: readonly { value: Gradient; label: string }[],
  value: Gradient,
): string | null {
  const same = (a: Gradient, b: Gradient) =>
    a.label === b.label && JSON.stringify(a.stops) === JSON.stringify(b.stops);
  return presets.find((p) => same(p.value, value))?.label ?? null;
}

/** The HSV whose screen color is `hex`, unrounded, so it shows as `hex`
 * again. Null for text that is not `#rrggbb`. */
export function hexToHsv(hex: string): Hsv | null {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) return null;
  const [r, g, b] = [0, 2, 4].map(
    (i) => (Number.parseInt(m[1].slice(i, i + 2), 16) / 255) ** DISPLAY_GAMMA,
  );
  const max = Math.max(r, g, b);
  const d = max - Math.min(r, g, b);
  let h = 0;
  if (d > 0) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
  }
  return {
    h: (h * 60 + 360) % 360,
    s: max > 0 ? d / max : 0,
    v: max,
  };
}

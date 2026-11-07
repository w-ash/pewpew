import { isFiniteNumber, isRecord, text, type Gradient, type PaletteParam, type Preset, type Stop } from "../schema";
import { decodeParts, fitParts, PARTS, readHsv } from "./color";
import { withDefault, type KindDef } from "./kind";

export const STOP_PARTS = ["at", ...PARTS] as const;

function readStop(json: unknown): Stop | undefined {
  const hsv = readHsv(json);
  return hsv && isRecord(json) && isFiniteNumber(json.at) ? { at: json.at, ...hsv } : undefined;
}

/** The gradient that JSON holds, or undefined: 2 to `maxStops` stops in
 * order from 0 to 1, and a label that is text or left out. */
function readGradient(json: unknown, maxStops: number): Gradient | undefined {
  if (!isRecord(json) || !Array.isArray(json.stops) || !(json.label === undefined || typeof json.label === "string")) {
    return undefined;
  }
  const stops: Stop[] = [];
  for (const raw of json.stops) {
    const stop = readStop(raw);
    if (!stop || stop.at < (stops.at(-1)?.at ?? 0)) return undefined;
    stops.push(stop);
  }
  const ends = stops[0]?.at === 0 && stops.at(-1)?.at === 1;
  return ends && stops.length >= 2 && stops.length <= maxStops ? { label: text(json.label), stops } : undefined;
}

const equalStop = (a: Stop, b: Stop) => STOP_PARTS.every((k) => a[k] === b[k]);

export const palette: KindDef<PaletteParam> = {
  decode(raw, common) {
    const stop = decodeParts(raw.stop, STOP_PARTS);
    const maxStops = raw.max_stops;
    if (!stop || typeof maxStops !== "number" || !Number.isInteger(maxStops) || maxStops < 2 || !Array.isArray(raw.presets)) {
      return null;
    }
    const presets: Preset[] = [];
    for (const preset of raw.presets) {
      if (!isRecord(preset) || typeof preset.label !== "string") return null;
      const value = readGradient(preset.value, maxStops);
      if (!value) return null;
      presets.push({ value, label: preset.label });
    }
    return withDefault(palette, { ...common, kind: "palette", stop, maxStops, presets }, raw);
  },
  read: (p, json) => readGradient(json, p.maxStops),
  /** A preset goes as declared, as reset sends the default. Otherwise each
   * part an edit changed is fitted, the ends stay at 0 and 1, and a stop
   * moved past a neighbour stops there, so every stop keeps its place. */
  normalize(p, g, prev) {
    if (p.presets.some((preset) => palette.equal(preset.value, g))) return g;
    const same = g.stops.length === prev.stops.length;
    const stops: Stop[] = g.stops.map((stop, i) => {
      const was = same ? prev.stops[i] : prev.stops.find((old) => equalStop(old, stop));
      return fitParts(p.stop, STOP_PARTS, stop, was);
    });
    const last = stops.length - 1;
    stops.forEach((stop, i) => {
      const moved = same && stop.at !== prev.stops[i]?.at;
      const lo = stops[i - 1]?.at ?? 0, hi = stops[i + 1]?.at ?? 1;
      const at = i === 0 ? 0 : i === last ? 1 : moved ? Math.min(Math.max(stop.at, lo), hi) : stop.at;
      stops[i] = { ...stop, at };
    });
    if (stops.some((stop, i) => stop.at < (stops[i - 1]?.at ?? 0))) stops.sort((a, b) => a.at - b.at);
    return { label: g.label, stops };
  },
  equal: (a, b) => a.label === b.label && a.stops.length === b.stops.length && a.stops.every((s, i) => equalStop(s, b.stops[i]!)),
  format: (_p, g) => g.label || `${g.stops.length} stops`,
};

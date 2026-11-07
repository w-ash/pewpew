import { formatPart } from "../format";
import { decodeNumberSpec, fitNumber, isFiniteNumber, isRecord, text, type ColorParam, type HSV, type Part } from "../schema";
import { withDefault, type KindDef } from "./kind";

export const PARTS = ["h", "s", "v"] as const;

/** A part's record, or null when it is malformed. */
function decodePart(raw: unknown): Part | null {
  if (!isRecord(raw)) return null;
  const spec = decodeNumberSpec(raw);
  return spec && { ...spec, label: text(raw.label) };
}

/** The record of each part in `keys`, from `raw` by name, or null when one is missing or malformed. */
export function decodeParts<K extends string>(raw: unknown, keys: readonly K[]): Record<K, Part> | null {
  if (!isRecord(raw)) return null;
  const out = {} as Record<K, Part>;
  for (const k of keys) {
    const part = decodePart(raw[k]);
    if (!part) return null;
    out[k] = part;
  }
  return out;
}

/** `v`, an edit of `prev`, with each part the edit changed fitted to its
 * spec. A part left as in `prev` is kept as is, so a value between steps
 * moves only where the operator moved it; without `prev`, every part is fitted. */
export function fitParts<K extends string>(
  parts: Readonly<Record<K, Part>>,
  keys: readonly K[],
  v: Readonly<Record<K, number>>,
  prev: Readonly<Record<K, number>> | undefined,
): Record<K, number> {
  const out = {} as Record<K, number>;
  for (const k of keys) out[k] = prev && v[k] === prev[k] ? v[k] : fitNumber(parts[k], v[k]);
  return out;
}

/** The color that JSON holds, or undefined. */
export function readHsv(json: unknown): HSV | undefined {
  if (!isRecord(json)) return undefined;
  const { h, s, v } = json;
  return isFiniteNumber(h) && isFiniteNumber(s) && isFiniteNumber(v) ? { h, s, v } : undefined;
}

export const color: KindDef<ColorParam> = {
  decode(raw, common) {
    const parts = decodeParts(raw.parts, PARTS);
    return parts && withDefault(color, { ...common, kind: "color", parts }, raw);
  },
  read: (_p, json) => readHsv(json),
  normalize: (p, c, prev) => fitParts(p.parts, PARTS, c, prev),
  equal: (a, b) => a.h === b.h && a.s === b.s && a.v === b.v,
  format: (p, c) => PARTS.map((k) => formatPart(p.parts[k], c[k])).join(" · "),
};

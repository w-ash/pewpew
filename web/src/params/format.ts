import { rounded, stepNumber, wrapNumber, type NumberSpec } from "./schema";

// The reader's own locale, which typed entry also parses with: a phone's
// decimal keypad offers only its locale's separator ("0,25" in de-DE).
export const LOCALE = globalThis.navigator?.language ?? "en-US";
const formats = new Map<number, Intl.NumberFormat>();

/** The Intl options every number on the page is written with. */
export function numberFormatOptions(decimals: number): Intl.NumberFormatOptions {
  return { minimumFractionDigits: decimals, maximumFractionDigits: decimals, useGrouping: false, signDisplay: "negative" };
}

function numberFormat(decimals: number): Intl.NumberFormat {
  let f = formats.get(decimals);
  if (!f) {
    f = new Intl.NumberFormat(LOCALE, numberFormatOptions(decimals));
    formats.set(decimals, f);
  }
  return f;
}

/** The number alone, at the spec's decimals: what typed entry shows. */
export function numberText(spec: NumberSpec, v: number): string {
  return numberFormat(spec.decimals).format(v);
}

/** The `text` label that matches `v` at the shown precision, or null. */
function textLabel(spec: NumberSpec, v: number): string | null {
  const shown = rounded(v, spec.decimals);
  return spec.text.find((t) => rounded(t.value, spec.decimals) === shown)?.label ?? null;
}

/** `n` and `unit` as the page writes them: a degree or percent sign against the number, any other
 * unit a space after it. */
export function withUnit(n: string, unit: string): string {
  return !unit ? n : unit === "°" || unit === "%" ? `${n}${unit}` : `${n} ${unit}`;
}

/** The text a numeric value reads as: its `text` label where one matches,
 * else the number at `decimals` digits and the unit. */
export function formatNumber(spec: NumberSpec, v: number): string {
  return textLabel(spec, v) ?? withUnit(numberText(spec, v), spec.unit);
}

/** What typed entry shows after the number: the `text` label where one matches, else the unit. */
export function numberSuffix(spec: NumberSpec, v: number): string {
  return textLabel(spec, v) ?? spec.unit;
}

/** Why `typed` (parsed as `n`) was not taken as typed, or null when it was:
 * not a number, outside the range, or between steps. A periodic value past
 * an end wraps, and the note says so only when it is also moved onto a step. */
export function typedNote(spec: NumberSpec, typed: string, n: number): string | null {
  if (!typed.trim()) return null;
  if (Number.isNaN(n)) return `‘${typed}’ is not a number`;
  const wrapped = wrapNumber(spec, n);
  const kept = stepNumber(spec, wrapped);
  if (!spec.periodic && (n < spec.lo || n > spec.hi)) {
    return `${typed} is outside ${numberText(spec, spec.lo)}…${numberText(spec, spec.hi)}: kept to ${numberText(spec, kept)}`;
  }
  if (Math.abs(kept - wrapped) < spec.step * 1e-6) return null; // wrap arithmetic leaves float noise
  const was = wrapped === n ? `${typed} is` : `${typed} wraps to ${numberText(spec, wrapped)},`;
  return `${was} between steps of ${numberText(spec, spec.step)}: kept to ${numberText(spec, kept)}`;
}

/** A 0..1 level as a whole percent. */
export function percent(v: number): string {
  return `${Math.round(v * 100)}%`;
}

/** `spec` read as a percent, when it is a 0..1 level with no unit (a color's saturation or
 * brightness, a layer's opacity), else null: shown at 100 times its value, in whole percents, as
 * the master is. */
export function percentOf(spec: NumberSpec): NumberSpec | null {
  if (spec.lo !== 0 || spec.hi !== 1 || spec.unit) return null;
  const scale = (v: number) => rounded(v * 100, spec.decimals);
  return {
    ...spec,
    hi: 100,
    step: Math.max(Math.round(scale(spec.step)), 1),
    decimals: 0,
    unit: "%",
    text: spec.text.map((t) => ({ ...t, value: scale(t.value) })),
  };
}

/** `v` as the entry of `spec` shows it: a 0..1 level with no unit as a percent (`percentOf`). */
export function formatPart(spec: NumberSpec, v: number): string {
  const pct = percentOf(spec);
  return pct ? formatNumber(pct, v * 100) : formatNumber(spec, v);
}

// Param records as the engine describes them (pewpew.params spec()).

export interface TextLabel {
  readonly value: number;
  readonly label: string;
}

/** The numeric record shared by float, int and each part of a compound value. */
export interface NumberSpec {
  readonly lo: number;
  readonly hi: number;
  readonly step: number;
  readonly decimals: number;
  readonly periodic: boolean;
  readonly unit: string;
  readonly text: readonly TextLabel[];
}

/** The fields every record has. A missing label, help, group or widget is "". `layer` and `node`
 * say which layer and node of the running look a knob belongs to: `node` is "" for a layer's own
 * mix (opacity, blend, enabled), and both are "" for a record that names no layer. */
export interface Common {
  readonly name: string;
  readonly label: string;
  readonly help: string;
  readonly group: string;
  readonly widget: string;
  readonly layer: string;
  readonly node: string;
}

export interface HSV {
  readonly h: number;
  readonly s: number;
  readonly v: number;
}

/** A numeric part of a compound value: a color's h, s or v; a palette stop's at. */
export interface Part extends NumberSpec {
  readonly label: string;
}

/** One color of a gradient, at a position from 0 to 1. */
export interface Stop extends HSV {
  readonly at: number;
}

/** Colors along 0..1: stops in order of `at`, the first at 0 and the last at 1. `label` names a preset, or is "". */
export interface Gradient {
  readonly label: string;
  readonly stops: readonly Stop[];
}

export interface Preset {
  readonly value: Gradient;
  readonly label: string;
}

export interface Option {
  readonly value: string;
  readonly label: string;
}

export interface FloatParam extends Common, NumberSpec {
  readonly kind: "float";
  readonly default: number;
}
export interface IntParam extends Common, NumberSpec {
  readonly kind: "int";
  readonly default: number;
}
export interface BoolParam extends Common {
  readonly kind: "bool";
  readonly default: boolean;
}
export interface ChoiceParam extends Common {
  readonly kind: "choice";
  readonly default: string;
  readonly options: readonly Option[];
}
export interface ColorParam extends Common {
  readonly kind: "color";
  readonly default: HSV;
  readonly parts: { readonly h: Part; readonly s: Part; readonly v: Part };
}
export interface PaletteParam extends Common {
  readonly kind: "palette";
  readonly default: Gradient;
  /** The parts of each stop. */
  readonly stop: { readonly at: Part; readonly h: Part; readonly s: Part; readonly v: Part };
  readonly maxStops: number;
  readonly presets: readonly Preset[];
}
/** A record this page cannot read: a kind it does not know, or a malformed one. */
export interface UnknownParam extends Common {
  readonly kind: "unknown";
  readonly wireKind: string;
  readonly default: unknown;
}

export type Param = FloatParam | IntParam | BoolParam | ChoiceParam | ColorParam | PaletteParam | UnknownParam;

export type Kind = Exclude<Param["kind"], "unknown">;

/** A param's value: what its default holds. */
export type ValueOf<P extends Param> = P["default"];

export type WireRecord = Readonly<Record<string, unknown>>;

export function isRecord(x: unknown): x is WireRecord {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

export function isFiniteNumber(x: unknown): x is number {
  return typeof x === "number" && Number.isFinite(x);
}

export function text(x: unknown): string {
  return typeof x === "string" ? x : "";
}

export function decodeCommon(raw: WireRecord): Common | null {
  if (typeof raw.name !== "string" || !raw.name) return null;
  return {
    name: raw.name,
    label: text(raw.label),
    help: text(raw.help),
    group: text(raw.group),
    widget: text(raw.widget),
    layer: text(raw.layer),
    node: text(raw.node),
  };
}

/** The numeric fields of a record, or null when any is missing or out of order. */
export function decodeNumberSpec(raw: WireRecord): NumberSpec | null {
  const { lo, hi, step, decimals } = raw;
  if (!isFiniteNumber(lo) || !isFiniteNumber(hi) || !(lo < hi)) return null;
  if (!isFiniteNumber(step) || step <= 0) return null;
  if (!Number.isInteger(decimals) || (decimals as number) < 0) return null;
  const labels = raw.text;
  if (!Array.isArray(labels)) return null;
  const textLabels: TextLabel[] = [];
  for (const t of labels) {
    if (!isRecord(t) || !isFiniteNumber(t.value) || typeof t.label !== "string") return null;
    textLabels.push({ value: t.value, label: t.label });
  }
  return {
    lo,
    hi,
    step,
    decimals: decimals as number,
    periodic: raw.periodic === true,
    unit: text(raw.unit),
    text: textLabels,
  };
}

/** The caption a param shows: its label, else its name. */
export function caption(p: Common): string {
  return p.label || p.name;
}

/** `v` at `decimals` digits. */
export function rounded(v: number, decimals: number): number {
  const k = 10 ** decimals;
  return Math.round(v * k) / k;
}

/** `v` wrapped into range when the spec is periodic, else `v`. */
export function wrapNumber(spec: NumberSpec, v: number): number {
  if (!spec.periodic || (v >= spec.lo && v <= spec.hi)) return v;
  const span = spec.hi - spec.lo;
  return spec.lo + ((((v - spec.lo) % span) + span) % span);
}

/** `v` on the nearest step from `lo` at the spec's decimals, clamped into range. */
export function stepNumber(spec: NumberSpec, v: number): number {
  const stepped = spec.lo + Math.round((v - spec.lo) / spec.step) * spec.step;
  return Math.min(Math.max(rounded(stepped, spec.decimals), spec.lo), spec.hi);
}

/** One step from `v` towards `dir` (1 up, -1 down) on the spec's grid of steps from `lo`: from a
 * value on the grid the next one, and from one between steps the nearest that way. Not clamped. */
export function stepOff(spec: NumberSpec, v: number, dir: number): number {
  const k = (v - spec.lo) / spec.step;
  const near = Math.round(k);
  const next = Math.abs(k - near) < 1e-6 ? near + dir : dir > 0 ? Math.ceil(k) : Math.floor(k);
  return rounded(spec.lo + next * spec.step, spec.decimals);
}

/** `v` as the spec holds it: wrapped into range when periodic, else
 * clamped, and on a step. */
export function fitNumber(spec: NumberSpec, v: number): number {
  return stepNumber(spec, wrapNumber(spec, v));
}

import { formatNumber } from "../format";
import { decodeNumberSpec, fitNumber, isFiniteNumber, type FloatParam, type IntParam } from "../schema";
import { withDefault, type KindDef } from "./kind";

/** The KindDef of a number kind; `whole` marks int. */
export function numericKind<P extends FloatParam | IntParam>(kind: P["kind"], whole: boolean): KindDef<P> {
  const holds = (x: unknown): x is number => isFiniteNumber(x) && (!whole || Number.isInteger(x));
  const def: KindDef<P> = {
    decode(raw, common) {
      const spec = decodeNumberSpec(raw);
      if (!spec || (whole && !(Number.isInteger(spec.lo) && Number.isInteger(spec.hi)))) return null;
      return withDefault(def, { ...common, ...spec, kind } as Omit<P, "default">, raw);
    },
    read: (_p, json) => (holds(json) ? json : undefined),
    normalize: (p, v) => fitNumber(p, v),
    equal: (a, b) => a === b,
    format: (p, v) => formatNumber(p, v),
  };
  return def;
}

import type { Common, Param, ValueOf, WireRecord } from "../schema";

/** Everything the page knows about one kind, in one place. */
export interface KindDef<P extends Param> {
  /** The typed param from its record, or null when the record is malformed. */
  decode(raw: WireRecord, common: Common): P | null;
  /** The value that JSON on the wire holds, or undefined for one this param cannot hold. The value goes back on the wire as is. */
  read(p: P, json: unknown): ValueOf<P> | undefined;
  /** `v`, a control's edit of `prev`, as the param holds it (on its steps, in its range),
   * whichever control produced it. A part the edit left as in `prev` is kept as is: a value
   * between steps (a default, a look, a `--param`) moves only where the operator moved it. */
  normalize(p: P, v: ValueOf<P>, prev: ValueOf<P>): ValueOf<P>;
  equal(a: ValueOf<P>, b: ValueOf<P>): boolean;
  format(p: P, v: ValueOf<P>): string;
}

/** The param when its default is a value it can hold, else null. */
export function withDefault<P extends Param>(def: KindDef<P>, p: Omit<P, "default">, raw: WireRecord): P | null {
  const value = def.read(p as P, raw.default);
  return value === undefined ? null : ({ ...p, default: value } as P);
}

import { decodeCommon, isRecord, type Param, type UnknownParam, type ValueOf } from "../schema";
import { bool } from "./bool";
import { choice } from "./choice";
import { color } from "./color";
import { float } from "./float";
import { int } from "./int";
import type { KindDef } from "./kind";
import { palette } from "./palette";

const unknown: KindDef<UnknownParam> = {
  decode: () => null,
  read: (_p, json) => json,
  normalize: (_p, v) => v,
  equal: (a, b) => JSON.stringify(a) === JSON.stringify(b),
  format: (_p, v) => JSON.stringify(v) ?? "",
};

const defs = { float, int, bool, choice, color, palette, unknown } as const;

export function defOf<P extends Param>(p: P): KindDef<P> {
  return defs[p.kind] as unknown as KindDef<P>;
}

/** The typed param of a record. A record the page cannot read becomes an
 * UnknownParam, which the page shows but cannot set. */
export function decodeParam(raw: unknown): Param {
  const rec = isRecord(raw) ? raw : {};
  const common = decodeCommon(rec) ?? { name: "", label: "", help: "", group: "", widget: "", layer: "", node: "" };
  const wireKind = typeof rec.kind === "string" ? rec.kind : "";
  const def = wireKind !== "unknown" && Object.hasOwn(defs, wireKind) ? defs[wireKind as keyof typeof defs] : null;
  const p = def && common.name ? def.decode(rec, common) : null;
  return p ?? { ...common, kind: "unknown", wireKind, default: rec.default };
}

/** Whether the page can set `p`: false for a record it could not read. */
export function settable(p: Param): boolean {
  return p.kind !== "unknown";
}

export function readValue<P extends Param>(p: P, json: unknown): ValueOf<P> | undefined {
  return defOf(p).read(p, json);
}

export function equalValue<P extends Param>(p: P, a: ValueOf<P>, b: ValueOf<P>): boolean {
  return defOf(p).equal(a, b);
}

export function formatValue<P extends Param>(p: P, v: ValueOf<P>): string {
  return defOf(p).format(p, v);
}

import type { BoolParam } from "../schema";
import { withDefault, type KindDef } from "./kind";

export const bool: KindDef<BoolParam> = {
  decode: (raw, common) => withDefault(bool, { ...common, kind: "bool" }, raw),
  read: (_p, json) => (typeof json === "boolean" ? json : undefined),
  normalize: (_p, v) => v,
  equal: (a, b) => a === b,
  format: (_p, v) => (v ? "on" : "off"),
};

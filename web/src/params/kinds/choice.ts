import { isRecord, type ChoiceParam, type Option } from "../schema";
import { withDefault, type KindDef } from "./kind";

export const choice: KindDef<ChoiceParam> = {
  decode(raw, common) {
    if (!Array.isArray(raw.options) || !raw.options.length) return null;
    const options: Option[] = [];
    for (const o of raw.options) {
      if (!isRecord(o) || typeof o.value !== "string" || typeof o.label !== "string") return null;
      options.push({ value: o.value, label: o.label });
    }
    return withDefault(choice, { ...common, kind: "choice", options }, raw);
  },
  read: (p, json) => (typeof json === "string" && p.options.some((o) => o.value === json) ? json : undefined),
  normalize: (_p, v) => v,
  equal: (a, b) => a === b,
  format: (p, v) => p.options.find((o) => o.value === v)?.label ?? v,
};

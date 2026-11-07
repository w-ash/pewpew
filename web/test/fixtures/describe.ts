import { decodeParam } from "../../src/domain/params/kinds";
import type { Param } from "../../src/domain/params/schema";
import describe from "../../../tests/goldens/describe.json";

/** Every pattern's param records, as the engine's describe golden holds them. */
export const PATTERNS = describe.patterns as Record<string, Record<string, unknown>[]>;
export const DISPLAY_GAMMA: number = describe.display_gamma;

export function record(pattern: string, name: string): Record<string, unknown> {
  const r = PATTERNS[pattern]?.find((x) => x.name === name);
  if (!r) throw new Error(`no ${pattern}.${name} in describe.json`);
  return r;
}

/** The decoded param `pattern.name`. */
export function param(pattern: string, name: string): Param {
  return decodeParam(record(pattern, name));
}

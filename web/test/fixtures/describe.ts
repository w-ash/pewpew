import { decodeParam } from "../../src/params/kinds";
import type { Param } from "../../src/params/schema";
import describe from "../../../tests/goldens/describe.json";

/** Every built-in op's param records, as the engine's describe golden holds them, and `zoo_test`, an
 * op with one param of each kind. */
export const OPS = describe.ops as Record<string, Record<string, unknown>[]>;
export const DISPLAY_GAMMA: number = describe.display_gamma;

export function record(op: string, name: string): Record<string, unknown> {
  const r = OPS[op]?.find((x) => x.name === name);
  if (!r) throw new Error(`no ${op}.${name} in describe.json`);
  return r;
}

/** The decoded param `op.name`. */
export function param(op: string, name: string): Param {
  return decodeParam(record(op, name));
}

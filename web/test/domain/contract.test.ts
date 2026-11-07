import { expect, test } from "vitest";
import { decodeParam, readValue } from "../../src/params/kinds";
import { OPS } from "../fixtures/describe";

const records = Object.entries(OPS).flatMap(([op, rs]) => rs.map((r) => [`${op}.${r.name}`, r] as const));

test("describe.json covers every kind", () => {
  const kinds = new Set(records.map(([, r]) => r.kind));
  expect([...kinds].sort()).toEqual(["bool", "choice", "color", "float", "int", "palette"]);
});

test.each(records)("%s decodes, and reads back its default as sent", (_id, r) => {
  const p = decodeParam(r);
  expect(p.kind).toBe(r.kind);
  expect(readValue(p, r.default)).toEqual(r.default);
});

import { expect, test } from "vitest";
import { typedNote } from "../../src/params/format";
import type { NumberSpec } from "../../src/params/schema";

const level: NumberSpec = { lo: 0, hi: 1, step: 0.005, decimals: 3, periodic: false, unit: "", text: [] };
const phase: NumberSpec = { ...level, periodic: true };
const hue: NumberSpec = { lo: 0, hi: 360, step: 2, decimals: 0, periodic: true, unit: "°", text: [] };

test("a typed number gets a note only when it was not taken as typed", () => {
  expect(typedNote(level, "", Number.NaN)).toBeNull();
  expect(typedNote(level, "x", Number.NaN)).toBe("‘x’ is not a number");
  expect(typedNote(level, "0.3", 0.3)).toBeNull();
  expect(typedNote(level, "5", 5)).toBe("5 is outside 0.000…1.000: kept to 1.000");
  expect(typedNote(level, "0.1234", 0.1234)).toBe("0.1234 is between steps of 0.005: kept to 0.125");
});

test("a periodic number past an end wraps quietly unless it also moves onto a step", () => {
  expect(typedNote(phase, "1.3", 1.3)).toBeNull();
  expect(typedNote(hue, "370", 370)).toBeNull();
  expect(typedNote(hue, "201", 201)).toBe("201 is between steps of 2: kept to 202");
  expect(typedNote(hue, "371", 371)).toBe("371 wraps to 11, between steps of 2: kept to 12");
});

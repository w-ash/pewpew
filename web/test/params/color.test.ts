import { expect, test } from "vitest";
import type { HSV } from "../../src/params/schema";
import { blendHsv, displayRgb, gradientCss, linearRgb, toDisplay } from "../../src/params/color";

test("linear HSV matches pewpew.color.hsv at the primaries and between", () => {
  const rgb = (h: number, s: number, v: number) => linearRgb({ h, s, v }).map((c) => +c.toFixed(9));
  expect(rgb(0, 1, 1)).toEqual([1, 0, 0]);
  expect(rgb(120, 1, 1)).toEqual([0, 1, 0]);
  expect(rgb(240, 1, 1)).toEqual([0, 0, 1]);
  expect(rgb(360, 1, 1)).toEqual([1, 0, 0]);
  expect(rgb(-120, 1, 1)).toEqual([0, 0, 1]);
  expect(rgb(30, 0.5, 0.8)).toEqual([0.8, 0.6, 0.4]);
});

test("display RGB applies the display gamma, as to_display_u8 does", () => {
  expect(toDisplay(0.5, 2.2)).toBe(186);
  expect(toDisplay(0, 2.2)).toBe(0);
  expect(toDisplay(2, 2.2)).toBe(255);
  expect(displayRgb({ h: 0, s: 0, v: 0.5 }, 2.2)).toEqual([186, 186, 186]);
});

test("a gradient is drawn through its stops' display colors, blended in OKLab", () => {
  const css = gradientCss({ label: "", stops: [{ at: 0, h: 0, s: 0, v: 0.5 }, { at: 0.355, h: 0, s: 1, v: 1 }, { at: 1, h: 240, s: 1, v: 1 }] }, 2.2);
  expect(css).toBe("linear-gradient(to right in oklab, rgb(186, 186, 186) 0%, rgb(255, 0, 0) 35.5%, rgb(0, 0, 255) 100%)");
  expect(CSS.supports("background-image", css)).toBe(true);
});

test("blendHsv matches the engine's gradient table (pewpew.color.gradient_lut) between two stops", () => {
  // Entry i of a table for stops at 0 and 1 is the blend at w = (i + 0.5) / 256, as HSV; the last is outside the gamut.
  const cases: [HSV, HSV, number, HSV][] = [
    [{ h: 0, s: 1, v: 0.35 }, { h: 210, s: 0.95, v: 0.4 }, 0.248046875, { h: 0.63, s: 0.84205, v: 0.28162 }],
    [{ h: 240, s: 1, v: 1 }, { h: 120, s: 1, v: 1 }, 0.498046875, { h: 190.9845, s: 1, v: 0.45799 }],
    [{ h: 0, s: 1, v: 1 }, { h: 180, s: 1, v: 1 }, 0.748046875, { h: 162.8865, s: 0.45116, v: 0.66832 }],
  ];
  for (const [a, b, w, want] of cases) {
    const got = blendHsv(a, b, w);
    expect(got.h).toBeCloseTo(want.h, 1);
    expect(got.s).toBeCloseTo(want.s, 2);
    expect(got.v).toBeCloseTo(want.v, 2);
  }
});

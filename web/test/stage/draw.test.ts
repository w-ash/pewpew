import { expect, test } from "vitest";
import type { Layout } from "../../src/room/layout";
import { drawScene, newLayers } from "../../src/stage/draw";

/** The centre pixel of `dots` dots of color `rgb` drawn on one spot; with
 * `rgb` null, the background the dots are added onto. */
function centre(rgb: number[] | null, dots: number): number[] {
  const canvas = Object.assign(document.createElement("canvas"), { width: 60, height: 60 });
  const ctx = canvas.getContext("2d")!;
  const layout: Layout = {
    n: dots,
    px: new Float32Array(dots).fill(30),
    py: new Float32Array(dots).fill(30),
    radii: new Float32Array(dots).fill(8),
    glow: 8.8,
    fixtures: [],
    plan: null,
  };
  const frame = rgb && Uint8Array.from({ length: 3 * dots }, (_, i) => rgb[i % 3]!);
  drawScene(ctx, newLayers({ bg: "#0b0b0e", marker: "#d99a2b" }), { layout, rgb: frame, plan: null, markers: false, dpr: 1 });
  return [...ctx.getImageData(30, 30, 1, 1).data.slice(0, 3)];
}

test.each([1, 4])("%i dots on one spot show the LED's color on the background, not white", (dots) => {
  const led = [133, 117, 148];
  const bg = centre(null, dots);
  const got = centre(led, dots);
  led.forEach((c, i) => expect(Math.abs(got[i]! - Math.min(255, c + bg[i]!))).toBeLessThanOrEqual(1));
});

test("a fixture layout mode picked shows as a band under its LEDs", () => {
  const canvas = Object.assign(document.createElement("canvas"), { width: 60, height: 60 });
  const ctx = canvas.getContext("2d")!;
  const fixture = { id: "a", ax: 10, ay: 30, bx: 50, by: 30, input: "start" as const };
  const layout: Layout = { n: 0, px: new Float32Array(), py: new Float32Array(), radii: new Float32Array(), glow: 0, fixtures: [fixture], plan: null };
  const at = (picked: typeof fixture | null) => {
    drawScene(ctx, newLayers({ bg: "#0b0b0e", marker: "#d99a2b" }), { layout, rgb: null, plan: null, markers: false, picked, dpr: 1 });
    return [...ctx.getImageData(30, 33, 1, 1).data.slice(0, 3)];
  };
  expect(at(null)).toEqual([11, 11, 14]);
  const [r, g, b] = at(fixture);
  expect(r).toBeGreaterThan(80);
  expect(r).toBeGreaterThan(b! * 2);
  expect(g).toBeLessThan(r!);
});

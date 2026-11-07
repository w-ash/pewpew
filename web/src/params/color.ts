// The only color math on the page. A color param is HSV over linear-light
// primaries, the same as pewpew.kit.hsv; the screen wants display-gamma RGB,
// as the engine's to_display_u8 gives the canvas.
import type { Gradient, HSV } from "./schema";

export type RGB = readonly [number, number, number];

/** Linear-light RGB in 0..1 for `hsv` (h in degrees, wrapping; s and v in 0..1). */
export function linearRgb({ h, s, v }: HSV): RGB {
  const h6 = ((((h / 360) % 1) + 1) % 1) * 6;
  const chan = (n: number) => {
    const k = (n + h6) % 6;
    return v - v * s * Math.min(Math.max(Math.min(k, 4 - k), 0), 1);
  };
  return [chan(5), chan(3), chan(1)];
}

/** One linear-light channel as an 8-bit display value. */
export function toDisplay(c: number, gamma: number): number {
  return Math.round(255 * Math.min(Math.max(c, 0), 1) ** (1 / gamma));
}

/** The 8-bit display RGB the canvas shows for `hsv`. */
export function displayRgb(hsv: HSV, gamma: number): RGB {
  const [r, g, b] = linearRgb(hsv);
  return [toDisplay(r, gamma), toDisplay(g, gamma), toDisplay(b, gamma)];
}

export function cssRgb([r, g, b]: RGB): string {
  return `rgb(${r}, ${g}, ${b})`;
}

/** A CSS gradient from left to right through `g`'s stops as the LEDs show
 * them, blended in OKLab as the engine blends (pewpew.color.gradient_lut). */
export function gradientCss(g: Gradient, gamma: number): string {
  const stops = g.stops.map((s) => `${cssRgb(displayRgb(s, gamma))} ${+(s.at * 100).toFixed(2)}%`);
  return `linear-gradient(to right in oklab, ${stops.join(", ")})`;
}

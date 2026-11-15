// The only color math on the page. A color param is HSV over linear-light
// primaries, the same as pewpew.color.hsv; the screen wants display-gamma RGB,
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

type M3 = readonly [RGB, RGB, RGB];

// Linear sRGB to cone response, cube-rooted cone response to OKLab, and their inverses: Björn Ottosson's
// matrices, the ones pewpew.color.lab holds.
const RGB_LMS: M3 = [[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]];
const LMS_LAB: M3 = [[0.2104542553, 0.793617785, -0.0040720468], [1.9779984951, -2.428592205, 0.4505937099], [0.0259040371, 0.7827717662, -0.808675766]];
const LAB_LMS: M3 = [[1, 0.3963377774, 0.2158037573], [1, -0.1055613458, -0.0638541728], [1, -0.0894841775, -1.291485548]];
const LMS_RGB: M3 = [[4.0767416621, -3.3077115913, 0.2309699292], [-1.2684380046, 2.6097574011, -0.3413193965], [-0.0041960863, -0.7034186147, 1.707614701]];

const mul = (m: M3, [x, y, z]: RGB): RGB => [
  m[0][0] * x + m[0][1] * y + m[0][2] * z,
  m[1][0] * x + m[1][1] * y + m[1][2] * z,
  m[2][0] * x + m[2][1] * y + m[2][2] * z,
];
const oklab = (rgb: RGB): RGB => mul(LMS_LAB, mul(RGB_LMS, rgb).map(Math.cbrt) as unknown as RGB);
const fromOklab = (lab: RGB): RGB => mul(LMS_RGB, mul(LAB_LMS, lab).map((c) => c ** 3) as unknown as RGB);
const inGamut = (rgb: RGB) => rgb.every((c) => c >= -1e-4 && c <= 1 + 1e-4);

/** The HSV (h in degrees) of linear-light `rgb`; a gray takes `hue`, and black `sat` too. */
function hsvOf([r, g, b]: RGB, hue: number, sat: number): HSV {
  const v = Math.max(r, g, b), d = v - Math.min(r, g, b);
  if (d <= 0) return { h: hue, s: v > 0 ? 0 : sat, v };
  const h6 = v === r ? ((g - b) / d + 6) % 6 : v === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return { h: h6 * 60, s: d / v, v };
}

/** The color the engine shows `w` (0 to 1) of the way from `a` to `b`: on the straight line between them in
 * OKLab, losing chroma until it fits the gamut, as pewpew.color.gradient_lut blends. */
export function blendHsv(a: HSV, b: HSV, w: number): HSV {
  const la = oklab(linearRgb(a)), lb = oklab(linearRgb(b));
  const [l, ca, cb] = la.map((x, i) => x + (lb[i]! - x) * w) as unknown as RGB;
  let rgb = fromOklab([l, ca, cb]);
  if (!inGamut(rgb)) {
    let lo = 0, hi = 1;
    for (let n = 0; n < 16; n++) {
      const mid = (lo + hi) / 2;
      if (inGamut(fromOklab([l, ca * mid, cb * mid]))) lo = mid;
      else hi = mid;
    }
    rgb = fromOklab([l, ca * lo, cb * lo]);
  }
  return hsvOf(rgb.map((c) => Math.min(Math.max(c, 0), 1)) as unknown as RGB, w < 0.5 ? a.h : b.h, w < 0.5 ? a.s : b.s);
}

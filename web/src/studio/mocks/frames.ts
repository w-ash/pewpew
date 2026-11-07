/**
 * Fake engine output for the mock session: display-ready RGB frames. Nothing
 * here resembles what pewpew renders.
 */
import { MOCK_PIXELS_PER_BAR } from "./catalog";

function hue(h: number, level: number, out: Uint8Array, at: number) {
  const k = (n: number) => (n + h * 6) % 6;
  const f = (n: number) => 1 - Math.max(0, Math.min(k(n), 4 - k(n), 1));
  out[at] = Math.round(255 * f(5) * level);
  out[at + 1] = Math.round(255 * f(3) * level);
  out[at + 2] = Math.round(255 * f(1) * level);
}

/** A rainbow that drifts along each bar, one hue band per layer of the look, at the master's level. */
export function renderMockFrame(
  layers: number,
  level: number,
  n: number,
  t: number,
): Uint8Array {
  const rgb = new Uint8Array(n * 3);
  for (let i = 0; i < n; i++) {
    const j = i % MOCK_PIXELS_PER_BAR;
    const h = ((((j / MOCK_PIXELS_PER_BAR) * layers - t * 0.25) % 1) + 1) % 1;
    hue(h, level, rgb, i * 3);
  }
  return rgb;
}

/** Watts if each pixel drew 0.4 W at full white, from linear light (gamma 2.2). */
export function mockWatts(rgb: Uint8Array): number {
  let sum = 0;
  for (let i = 0; i < rgb.length; i++) sum += (rgb[i]! / 255) ** 2.2;
  return (sum / 3) * 0.4;
}

// The brightness (the master dimmer) and its launch-time cap, which the page calls its max.
import { percent } from "../params/format";
import { rounded } from "../params/schema";

/** What one press of the brightness's − or + moves it by. */
export const MASTER_STEP = 0.05;

/** The cap in words, `max 80%`; "" when there is none. */
export function capText(cap: number): string {
  return cap < 1 ? `max ${percent(cap)}` : "";
}

/** `v` moved `steps` presses, on the 0.01 grid, within 0..cap. */
export function stepMaster(v: number, cap: number, steps: number): number {
  return Math.min(Math.max(rounded(v + steps * MASTER_STEP, 2), 0), cap);
}

// The knob this page set last, so an error that follows can name it and put it back.
import { useSyncExternalStore } from "react";
import type { Param } from "./schema";

/** A set of knob `p` from this page: its value when the edit began (`from`), what it was set to, and when. */
export interface LastSet {
  readonly p: Param;
  readonly from: unknown;
  readonly to: unknown;
  readonly at: number;
}

/** How long sets of one knob read as one edit, and an error after the last as its doing. */
export const EDIT_MS = 5000;

let last: LastSet | null = null;
const listeners = new Set<() => void>();

/** Note a set of `p` to `to`, from `from`, the value the engine had: sets of one knob within EDIT_MS
 * of each other are one edit, from the first one's value. */
export function noteSet(p: Param, from: unknown, to: unknown, now = performance.now()): void {
  const run = last !== null && last.p.name === p.name && now - last.at < EDIT_MS;
  last = { p, from: run ? last!.from : from, to, at: now };
  for (const l of listeners) l();
}

export function useLastSet(): LastSet | null {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => last,
  );
}

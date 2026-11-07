import type { KeyboardEvent } from "react";

// The slider keys of the ARIA pattern, Right and Up increasing: one step, or
// ten with Shift or a Page key.
const KEYS: Readonly<Record<string, number>> = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 10, PageDown: -10 };
const PAGE = 10;

/** A capture handler that takes a slider's step keys from Zag and calls
 * `onStep` with how many of the param's own steps to move. Zag steps in its
 * own units (1° on a hue strip, 1% on saturation, the dial's turn), which a
 * coarser step snaps back from or a turned dial reverses. */
export function stepKeys(onStep: (steps: number) => void) {
  return (e: KeyboardEvent) => {
    const steps = KEYS[e.key];
    // A modified arrow is the browser's (Back, on Cmd or Alt).
    if (steps === undefined || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault();
    e.stopPropagation();
    onStep(e.shiftKey && Math.abs(steps) === 1 ? steps * PAGE : steps);
  };
}

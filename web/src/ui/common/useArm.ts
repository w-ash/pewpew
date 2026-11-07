// Two-tap actions: the first tap arms for ARM_MS, a second within it fires.
// A second tap sooner than CONFIRM_MIN_MS is a bounce or a nervous double
// tap, not a confirm, and does nothing. One action is armed at a time:
// arming one disarms the rest.
import { createContext, useContext, useEffect, useRef, useState, useSyncExternalStore } from "react";

export const ARM_MS = 3000;
export const CONFIRM_MIN_MS = 400;

/** The time an arm reads, for the double-tap guard and the lapse alike. */
export interface ArmClock {
  now(): number;
  /** Call `fn` once `ms` has passed. The result cancels the call. */
  after(ms: number, fn: () => void): () => void;
}

/** The clock two-press buttons read: real time, unless a test provides one that moves only when the test moves it. */
export const ArmClockContext = createContext<ArmClock>({
  now: () => performance.now(),
  after: (ms, fn) => {
    const id = setTimeout(fn, ms);
    return () => clearTimeout(id);
  },
});

const disarmers = new Set<() => void>();

// What the page's one polite status says of the button armed last: what its second press does.
let armedLine = "";
const lineListeners = new Set<() => void>();

/** Say `line` in the page's arm status (`ArmStatus`) while `on`; off, clear it unless another
 * button's line has replaced it. */
export function sayArmed(line: string, on: boolean): void {
  const next = on ? line : armedLine === line ? "" : armedLine;
  if (next === armedLine) return;
  armedLine = next;
  for (const l of lineListeners) l();
}

/** What the arm status says now. */
export function useArmedLine(): string {
  return useSyncExternalStore(
    (l) => {
      lineListeners.add(l);
      return () => lineListeners.delete(l);
    },
    () => armedLine,
  );
}

/** Disarm every armed action on the page (Esc, a lost connection). */
export function disarmAll(): void {
  for (const disarm of disarmers) disarm();
}

export interface Arm {
  readonly armed: boolean;
  /** Fire when armed long enough, else arm. */
  press(fire: () => void): void;
  disarm(): void;
}

export function useArm(): Arm {
  const clock = useContext(ArmClockContext);
  const [armed, setArmed] = useState(false);
  const cancelLapse = useRef<() => void>(undefined);
  const armedAt = useRef(0);
  const disarm = () => {
    cancelLapse.current?.();
    setArmed(false);
  };
  useEffect(() => {
    disarmers.add(disarm);
    return () => {
      disarmers.delete(disarm);
      cancelLapse.current?.();
    };
  }, []);
  const press = (fire: () => void) => {
    navigator.vibrate?.(10);
    if (armed) {
      if (clock.now() - armedAt.current < CONFIRM_MIN_MS) return;
      disarm();
      fire();
      return;
    }
    disarmAll();
    armedAt.current = clock.now();
    setArmed(true);
    cancelLapse.current = clock.after(ARM_MS, () => setArmed(false));
  };
  return { armed, press, disarm };
}

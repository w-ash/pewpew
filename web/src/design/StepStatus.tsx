import { useSyncExternalStore } from "react";

/** How long presses of − or + rest before the step status says where they left a value. */
const SETTLE_MS = 600;

// What the page's step status says.
let line = "";
let timer: ReturnType<typeof setTimeout> | undefined;
const listeners = new Set<() => void>();

function set(next: string): void {
  line = next;
  for (const l of listeners) l();
}

/** Say `text` (`brightness 75%`) in the page's step status once presses of − or + rest: a run of presses
 * says only where it ended. For a press that leaves focus on its button, whose name does not change. */
export function sayStep(text: string): void {
  clearTimeout(timer);
  if (line) set("");
  timer = setTimeout(() => set(text), SETTLE_MS);
}

/** The page's one polite status for steps (`sayStep`). */
export function StepStatus() {
  const said = useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => line,
  );
  return (
    <p className="sr-only" role="status">
      {said}
    </p>
  );
}

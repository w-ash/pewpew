// Drag capture: while a control is held, the value shown is the one under the
// finger, not the echo. After release the draft stays until the echo agrees,
// or SETTLE_MS passes (another tab won), so the control does not snap back
// to the old value while its own set is in flight.
import { useEffect, useState } from "react";

export const SETTLE_MS = 1000;

export interface Draft<V> {
  readonly shown: V;
  /** The control moved to `v`. */
  change(v: V): void;
  /** The control let go. */
  release(): void;
  /** Show the echo again now (a refusal). */
  drop(): void;
}

export function useDraft<V>(echoed: V, equal: (a: V, b: V) => boolean): Draft<V> {
  const [draft, setDraft] = useState<{ readonly v: V; readonly held: boolean } | null>(null);
  if (draft && !draft.held && equal(echoed, draft.v)) setDraft(null);
  useEffect(() => {
    if (!draft || draft.held) return;
    const id = setTimeout(() => setDraft(null), SETTLE_MS);
    return () => clearTimeout(id);
  }, [draft]);
  return {
    shown: draft ? draft.v : echoed,
    change: (v) => setDraft({ v, held: true }),
    release: () => setDraft((d) => d && { v: d.v, held: false }),
    drop: () => setDraft(null),
  };
}

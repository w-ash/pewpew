// The fade a press on a look takes: one choice for the deck's tiles and the list of every look.
import { useSyncExternalStore } from "react";
import { FADES } from "../aura/looks";

let chosen = FADES[0]!.value;
const listeners = new Set<() => void>();

function subscribe(l: () => void): () => void {
  listeners.add(l);
  return () => listeners.delete(l);
}

/** The fade chosen on this page (a `FADES` value), and how to choose another. */
export function useFade(): [string, (fade: string) => void] {
  const fade = useSyncExternalStore(subscribe, () => chosen);
  const set = (next: string) => {
    chosen = next;
    for (const l of listeners) l();
  };
  return [fade, set];
}

import { useSyncExternalStore } from "react";

const lists = new Map<string, MediaQueryList>();

function list(query: string): MediaQueryList {
  let m = lists.get(query);
  if (!m) lists.set(query, (m = matchMedia(query)));
  return m;
}

export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    (l) => {
      const m = list(query);
      m.addEventListener("change", l);
      return () => m.removeEventListener("change", l);
    },
    () => list(query).matches,
  );
}

/** The split layout, the canvas beside a side panel: a wide screen, or a
 * phone on its side, which has no height for the stacked one. A narrow
 * window with a mouse (a laptop zoomed in) stacks, as a phone held upright
 * does. Target sizes follow the pointer, not this (page.css). */
export const WIDE = "(min-width: 900px), (orientation: landscape) and (min-height: 300px) and (pointer: coarse)";
export const FINE_POINTER = "(pointer: fine)";

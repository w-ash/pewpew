import { useEffect, useRef } from "react";

/** How far in from each end of a row its item stays: the row's fade (page.css .scroller). */
const EDGE = 16;

/** A ref whose element its row scrolls to show when `key` changes: the current item of a row swiped
 * sideways on a phone stays on screen, clear of the row's faded ends, and of a wrapped row that
 * scrolls down (the wide deck's looks), in view. An item past the row's far end comes in to its near
 * end, where a row that snaps (the phone's looks) stops. Only the row moves, never the page or panel
 * around it. */
export function useInView<T extends HTMLElement>(key: unknown) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const item = ref.current, row = item?.parentElement;
    if (!item || !row) return;
    const a = item.getBoundingClientRect(), r = row.getBoundingClientRect();
    if (a.left < r.left + EDGE) row.scrollLeft -= r.left + EDGE - a.left;
    else if (a.right > r.right - EDGE) row.scrollLeft += a.left - (r.left + EDGE);
    if (a.top < r.top) row.scrollTop -= r.top - a.top;
    else if (a.bottom > r.bottom) row.scrollTop += a.bottom - r.bottom;
  }, [key]);
  return ref;
}

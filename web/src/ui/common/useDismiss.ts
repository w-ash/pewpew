import { useEffect, type RefObject } from "react";

/** While `open`, Esc, a press outside `ref`'s element or focus leaving it calls `close`, with whether
 * it was Esc: how a note that a press opened goes away. */
export function useDismiss(ref: RefObject<HTMLElement | null>, open: boolean, close: (esc: boolean) => void): void {
  useEffect(() => {
    if (!open) return;
    const outside = (e: Event) => {
      if (e.target instanceof Node && !ref.current?.contains(e.target)) close(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") close(true);
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", outside);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("focusin", outside);
      document.removeEventListener("keydown", esc);
    };
  }, [ref, open, close]);
}

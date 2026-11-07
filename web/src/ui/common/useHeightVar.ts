import { useCallback } from "react";

/** A ref that publishes its element's height as CSS variable `name` on the slot it scrolls in, while
 * the element is shown: what pins under it (page.css) and the slot's scroll padding read it. */
export function useHeightVar(name: string) {
  return useCallback(
    (el: HTMLElement | null) => {
      const slot = el?.closest<HTMLElement>(".slot");
      if (!el || !slot) return;
      const watch = new ResizeObserver(() => {
        if (el.offsetHeight) slot.style.setProperty(name, `${el.offsetHeight}px`);
      });
      watch.observe(el);
      return () => {
        watch.disconnect();
        slot.style.removeProperty(name);
      };
    },
    [name],
  );
}

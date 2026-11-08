import { useEffect, useId, useRef, type ReactNode, type Ref, type RefObject } from "react";
import { IconButton } from "./Button";
import { useHeightVar } from "./useHeightVar";

/** A panel's title, which `titleRef` can focus, and the ✕ that closes it: pinned at the slot's top. */
export function PanelHead({ titleId, title, onClose, titleRef }: { titleId: string; title: string; onClose(): void; titleRef?: Ref<HTMLHeadingElement> }) {
  return (
    <div ref={useHeightVar("--head-h")} className="panel-head">
      <h2 id={titleId} ref={titleRef} className="t-title" tabIndex={-1}>
        {title}
      </h2>
      <IconButton icon="close" label={`close ${title}`} onPress={onClose} />
    </div>
  );
}

/** A titled panel in the side slot, in place of the editor until its ✕, or Esc inside it, closes it. Open, it
 * starts at the slot's top, and takes focus to `focusRef`'s element, else its title, unless what it holds took it, so Esc closes it at
 * once; a press on its empty ground keeps focus in it, so Esc still does. Closed, it hands focus back to what
 * opened it, when nothing else took it. */
export function Panel({ id, title, onClose, focusRef, children }: { id?: string; title: string; onClose(): void; focusRef?: RefObject<HTMLElement | null>; children: ReactNode }) {
  const titleId = useId();
  const head = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    const panel = head.current?.closest("section");
    const slot = panel?.closest<HTMLElement>(".slot");
    if (slot) slot.scrollTop = 0;
    if (panel && !panel.contains(opener)) (focusRef?.current ?? head.current)?.focus({ preventScroll: true });
    return () => {
      if (opener instanceof HTMLElement && opener.isConnected && document.activeElement === document.body) opener.focus();
    };
  }, [focusRef]);
  return (
    <section
      id={id}
      className="panel"
      aria-labelledby={titleId}
      tabIndex={-1}
      onKeyDown={(e) => {
        if (e.key !== "Escape" || e.defaultPrevented) return;
        e.preventDefault();
        onClose();
      }}
    >
      <PanelHead titleId={titleId} title={title} onClose={onClose} titleRef={head} />
      {children}
    </section>
  );
}

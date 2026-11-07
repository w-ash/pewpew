import type { KeyboardEvent, ReactNode, Ref } from "react";
import { spaced } from "./spaced";

const MOVES: Readonly<Record<string, (i: number, n: number) => number>> = {
  ArrowRight: (i, n) => (i + 1) % n,
  ArrowDown: (i, n) => (i + 1) % n,
  ArrowLeft: (i, n) => (i - 1 + n) % n,
  ArrowUp: (i, n) => (i - 1 + n) % n,
  Home: () => 0,
  End: (_, n) => n - 1,
};

/** Tiles to pick from in a row that is one tab stop, a toolbar: the arrow keys, Home and End move between
 * its tiles. The tile that is the tab stop has tabIndex 0, every other -1. One row swiped sideways on touch
 * or a narrow screen, wrapped on a wide one with a mouse (`.scroller`). It is named by `label`, or by the
 * element `labelledBy` names. */
export function TileRow({ ref, className, label, labelledBy, children }: { ref?: Ref<HTMLDivElement>; className?: string; label?: string; labelledBy?: string; children: ReactNode }) {
  const roam = (e: KeyboardEvent<HTMLDivElement>) => {
    const move = MOVES[e.key];
    const buttons = [...e.currentTarget.querySelectorAll<HTMLButtonElement>(":scope > button")];
    const at = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (!move || at < 0) return;
    e.preventDefault();
    buttons[move(at, buttons.length)]?.focus();
  };
  return (
    <div ref={ref} className={spaced("scroller", className)} role="toolbar" aria-label={label} aria-labelledby={labelledBy} onKeyDown={roam}>
      {children}
    </div>
  );
}

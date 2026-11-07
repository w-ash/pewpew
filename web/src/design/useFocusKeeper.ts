import { useEffect, useRef } from "react";

/** What a control is across a render that replaces it: its knob (`data-param`), its role and its name. */
function keyOf(el: Element): string {
  const name = el.getAttribute("aria-label") ?? el.textContent?.trim() ?? "";
  return [el.closest("[data-param]")?.getAttribute("data-param") ?? "", el.getAttribute("role") ?? el.tagName, name].join("|");
}

/** Whether `el` can take focus now: in the page, shown and not inert. */
const usable = (el: HTMLElement) => el.isConnected && !el.closest("[inert]") && el.checkVisibility();

/** Focus `name`'s knob: its slider, list, switch or entry, when it is in the page. */
export function focusParam(name: string): void {
  document.querySelector<HTMLElement>(`[data-param="${CSS.escape(name)}"] :is([role=slider], select, [role=switch], input)`)?.focus();
}

/** Puts focus back when what held it went away under it: an aura message took it out of the page, or made it
 * inert (a cue's hold, a lost connection). It goes back to the control focused last by hand, or to
 * one like it (`keyOf`: its knob, role and name) once one can take it; meanwhile to the first of
 * `fallbacks` that can (a selector each, in turn), from which it moves on to that control once it is
 * back. A person who moved focus away keeps it there. Checked again whenever the `aura` or `lost`
 * changes. */
export function useFocusKeeper(fallbacks: readonly string[], aura: unknown, lost: boolean): void {
  // The control focused last by hand, and the element focused last by anyone.
  const home = useRef<{ el: HTMLElement; key: string } | null>(null);
  const last = useRef<HTMLElement | null>(null);
  const placing = useRef(false);
  // The fallback focus was put on, while it holds it: focus waits there for the control to come back.
  const placed = useRef<HTMLElement | null>(null);
  // Focus was taken, not moved: it stays to be put back until something has it again.
  const stranded = useRef(false);
  const restore = () => {
    const at = document.activeElement;
    // WebKit can leave focus on a control gone inert, without a blur.
    const inert = at instanceof HTMLElement && at !== document.body && !!at.closest("[inert]");
    const waiting = !!placed.current && at === placed.current;
    if (at && at !== document.body && !inert && !waiting) {
      stranded.current = false;
      return;
    }
    if (!stranded.current && !waiting) {
      if (!inert && (!last.current || usable(last.current))) return;
      stranded.current = true;
    }
    const h = home.current;
    const back = h && (usable(h.el) ? h.el : [...document.querySelectorAll<HTMLElement>("button, input, select, [tabindex]")].find((el) => keyOf(el) === h.key && usable(el)));
    const next = back || (waiting ? null : fallbacks.map((sel) => [...document.querySelectorAll<HTMLElement>(sel)].find(usable)).find(Boolean));
    if (!next) return;
    placing.current = !back;
    next.focus({ preventScroll: !back });
    placing.current = false;
    placed.current = back ? null : next;
  };
  useEffect(() => {
    const keep = (e: FocusEvent) => {
      if (!(e.target instanceof HTMLElement)) return;
      last.current = e.target;
      stranded.current = false;
      if (placing.current) return;
      placed.current = null;
      home.current = { el: e.target, key: keyOf(e.target) };
    };
    const left = () => requestAnimationFrame(restore);
    document.addEventListener("focusin", keep);
    document.addEventListener("focusout", left);
    return () => {
      document.removeEventListener("focusin", keep);
      document.removeEventListener("focusout", left);
    };
  // oxlint-disable-next-line react-hooks/exhaustive-deps -- restore reads refs and the constant `fallbacks`; the first render's copy stays right
  }, []);
  useEffect(() => {
    const id = requestAnimationFrame(restore);
    return () => cancelAnimationFrame(id);
  // oxlint-disable-next-line react-hooks/exhaustive-deps -- it re-checks when `aura` or `lost` changes, so it needs no other trigger
  }, [aura, lost]);
}

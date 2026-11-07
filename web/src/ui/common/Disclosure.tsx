// The "? note": a line that explains, opened inline under its row by a button, as the APG disclosure
// pattern has it (aria-expanded, aria-controls). One note is open on the page at a time; a second press
// or Esc closes it, and focus stays where it was.
import { useEffect, useId, useRef, useSyncExternalStore, type ReactNode } from "react";
import { IconButton } from "./Button";

interface Shown {
  readonly id: string;
  /** What the note says, when its opener gives it the words (a reason, a confirm's cost). */
  readonly text: string;
}

let shown: Shown | null = null;
const listeners = new Set<() => void>();

function set(next: Shown | null): void {
  shown = next;
  for (const l of listeners) l();
}

function subscribe(l: () => void): () => void {
  listeners.add(l);
  return () => listeners.delete(l);
}

/** Close note `id` while it is open; given `text`, only while it shows those words. It reads the store as it
 * is now, so a press that opens one note and an effect that closes another in the same commit agree. */
function shut(id: string, text?: string): void {
  if (shown?.id === id && (text === undefined || shown.text === text)) set(null);
}

export interface Disclosure {
  /** The note's id, which its button controls. */
  readonly id: string;
  readonly open: boolean;
  /** The words its opener gave it, or "". */
  readonly text: string;
  /** Open it, closing any other, with `text` as its words; or close it when it is open with them. */
  toggle(text?: string): void;
  show(text?: string): void;
  /** Close it while it is open; given `text`, only while it shows those words, so an opener closes what it
   * opened and never what another opener has put in its place. */
  close(text?: string): void;
}

/** A note of the page's one-open set, closed on Esc while open. */
export function useDisclosure(): Disclosure {
  const id = useId();
  const now = useSyncExternalStore(subscribe, () => shown);
  const open = now?.id === id;
  useEffect(() => {
    if (!open) return;
    // Captured at the document, so Esc closes the note and nothing else: not a panel, not an arm.
    const esc = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.stopPropagation();
      set(null);
    };
    document.addEventListener("keydown", esc, true);
    return () => document.removeEventListener("keydown", esc, true);
  }, [open]);
  // An unmounted opener takes its note with it.
  useEffect(() => () => shut(id), [id]);
  const show = (text = "") => set({ id, text });
  return {
    id,
    open,
    text: open ? (now?.text ?? "") : "",
    show,
    toggle: (text = "") => (shown?.id === id && shown.text === text ? set(null) : show(text)),
    close: (text?: string) => shut(id, text),
  };
}

/** The quiet "?" after a word that needs explaining; `label` names it ("about max"). `controls` names
 * what it shows, when that is more than its note. */
export function DisclosureButton({ disclosure, label, controls }: { disclosure: Disclosure; label: string; controls?: string }) {
  return (
    <IconButton
      glyph="?"
      label={label}
      className="about"
      aria-expanded={disclosure.open}
      aria-controls={controls ?? disclosure.id}
      onPress={() => disclosure.toggle()}
    />
  );
}

/** The note itself, in the page's flow under its row: `children`, else the words its opener gave it. Kept
 * in the page while shut, so the button's aria-controls resolves. `live`: a note a press opens, said as it
 * opens (a reason, what a second press does), for assistive tech that does not follow focus to it. A note
 * that leaves the page, taken out or hidden with what holds it, closes: it keeps no Esc, and it does not
 * come back unasked with its row. */
export function DisclosureNote({ disclosure, children, live }: { disclosure: Disclosure; children?: ReactNode; live?: boolean }) {
  const { id, open } = disclosure;
  const words = children ?? disclosure.text;
  const note = useRef<HTMLDivElement>(null);
  useEffect(() => () => shut(id), [id]);
  useEffect(() => {
    const el = note.current;
    if (!open || !el) return;
    // A box that stops being drawn resizes to nothing.
    const watch = new ResizeObserver(() => {
      if (!el.checkVisibility()) shut(id);
    });
    watch.observe(el);
    return () => watch.disconnect();
  }, [open, id]);
  return (
    <div ref={note} id={id} className="note disclosure-note" role={live ? "status" : undefined} hidden={!open || !words}>
      {open && words}
    </div>
  );
}

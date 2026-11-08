// The Console's layout editor and the engine's arrangement file: each edit, once edits settle, goes to the
// engine as one `arrange`; the engine's `arrangement` comes back as the file's new content. Undo and redo
// are this page's own history (doc.ts).
import { useEffect, useMemo, useRef, useState } from "react";
import { useSender, useWire } from "../wire/store";
import { asArrangement } from "./arrangement";
import { useDoc } from "./doc";
import type { Arrangement } from "./types";

/** How long the editor waits after an edit before it sends the arrangement: a drag of a number or a run
 * of key presses sends once. */
export const SETTLE_MS = 400;

/** Whether `a` and `b` are the same JSON value, whatever the order of their keys. */
export function sameJson(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true;
  if (typeof a !== "object" || typeof b !== "object" || a === null || b === null) return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const ka = Object.keys(a), kb = Object.keys(b);
  const ra = a as Record<string, unknown>, rb = b as Record<string, unknown>;
  return ka.length === kb.length && ka.every((k) => Object.hasOwn(rb, k) && sameJson(ra[k], rb[k]));
}

/** `arrangement` as the file holds it: an empty `groups` list, which the editor adds, left out, so an
 * undo back to a file without one writes the file it was. */
export function fileForm(arrangement: Arrangement): Arrangement {
  if (arrangement.groups.length > 0) return arrangement;
  const { groups: _, ...rest } = arrangement;
  return rest as Arrangement;
}

/** The engine's arrangement as the editor reads it: its fixtures and groups lists given even where the
 * file leaves them out, so the engine's echo of an edit compares equal to it. Null before one, and for
 * a file that is not an arrangement. */
export function useEngineArrangement(): Arrangement | null {
  const raw = useWire((s) => s.arrangement);
  return useMemo(() => (raw ? asArrangement(raw) : null), [raw]);
}

/** Whether the engine's arrangement is the editor's present one: its compile is then the compile of the
 * document, and poses read from it match what the editor holds. */
export function useRigIsCurrent(): boolean {
  const engine = useEngineArrangement();
  const present = useDoc((s) => s.history.present);
  return engine !== null && sameJson(engine, present);
}

/**
 * Keeps the editor's arrangement and the engine's together while the editor is open. The engine's
 * arrangement replaces the history when it is the first, or when it is neither the present one nor the
 * last one sent: a change from elsewhere (a save of the file, another tab), not the echo of an edit. Each
 * present arrangement the engine does not hold goes to it SETTLE_MS after the last edit; one still waiting
 * goes when the editor closes. Returns whether the engine refused the last one sent (its refusal, with
 * the issues, is the store's `arrange` refusal).
 */
export function useArrangeSync(): { readonly refused: boolean } {
  const engine = useEngineArrangement();
  const present = useDoc((s) => s.history.present);
  const sender = useSender();
  const sent = useRef<Arrangement | null>(null);
  const waiting = useRef<Arrangement | null>(null);
  const [refused, setRefused] = useState(false);

  const send = (arrangement: Arrangement) => {
    waiting.current = null;
    sent.current = arrangement;
    void sender.ask({ type: "arrange", arrangement: fileForm(arrangement) }).then((took) => setRefused(!took));
  };

  useEffect(() => {
    if (!engine) return;
    const doc = useDoc.getState();
    const held = doc.history.present;
    const echo = sameJson(engine, held) || (sent.current !== null && sameJson(engine, sent.current));
    if (doc.loads === 0 || !echo) {
      sent.current = null;
      waiting.current = null;
      doc.load(engine);
    }
  }, [engine]);

  useEffect(() => {
    if (!engine || sameJson(present, engine) || (sent.current !== null && sameJson(present, sent.current))) {
      waiting.current = null;
      return;
    }
    waiting.current = present;
    const id = setTimeout(() => send(present), SETTLE_MS);
    return () => clearTimeout(id);
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- `send` reads only refs and the sender
  }, [present, engine, sender]);

  useEffect(
    () => () => {
      if (waiting.current) send(waiting.current);
    },
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- runs once, when the editor closes
    [],
  );

  return { refused };
}

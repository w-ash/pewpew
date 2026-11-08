// The Console's layout editor and the engine's arrangement file: each edit, once edits settle, goes to the
// engine as one `arrange` that names the digest of the file it was built on (`base`); the engine's
// `arrangement` comes back as the file's new content. Undo and redo are this page's own history (doc.ts).
// The sync is one per page, shared by every panel that shows the editor, so a panel that closes while an
// edit settles neither drops it nor sends it twice.
import { useEffect, useMemo } from "react";
import { create } from "zustand";
import type { Sender } from "../wire/protocol";
import { useWire, useWireContext, type WireStore } from "../wire/store";
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
 * file leaves them out, so the engine's echo of an edit compares equal to it. Null before one, and while
 * the page may not edit it. */
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

/** What the panels read of the sync. */
interface SyncState {
  /** Whether the engine refused the last arrangement sent (its refusal is the store's `arrange` one). */
  readonly refused: boolean;
}

export const useArrangeSyncState = create<SyncState>()(() => ({ refused: false }));

/** The sync's own state, one per page: kept while no panel shows the editor, so an edit still settling
 * goes when its timer fires, and the engine's answer lands. */
const sync = {
  store: null as WireStore | null,
  sender: null as Sender | null,
  /** How many panels use the sync, and what they listen to while any does. */
  users: 0,
  off: null as (() => void) | null,
  /** The engine's arrangement last read, by identity: the store keeps it until a new one comes. */
  seen: null as unknown,
  /** The digest of the engine's arrangement the history builds on: the `base` of the next `arrange`. */
  base: null as string | null,
  /** Sent and not yet echoed or refused: one `arrange` at a time, so each names the base it edited. */
  inflight: null as Arrangement | null,
  /** The last arrangement sent, which is never sent again while the editor holds it (one refused). */
  lastSent: null as Arrangement | null,
  timer: null as ReturnType<typeof setTimeout> | null,
};

function reset(store: WireStore, sender: Sender): void {
  if (sync.timer) clearTimeout(sync.timer);
  Object.assign(sync, { store, sender, seen: null, base: null, inflight: null, lastSent: null, timer: null });
  useArrangeSyncState.setState({ refused: false });
}

/** Read the engine's arrangement when it is new. Its echo of the arrangement in flight keeps the
 * history; any other that is not the present one (a save of the file, a rebind, another tab) replaces
 * it, since its undo steps were built on a file that is gone. */
function reconcile(): void {
  const state = sync.store?.getState();
  if (!state || state.arrangement === sync.seen) return;
  sync.seen = state.arrangement;
  const engine = asArrangement(state.arrangement);
  if (!engine || state.arrangementBase === null) return;
  const doc = useDoc.getState();
  sync.base = state.arrangementBase;
  if (sync.inflight && sameJson(engine, sync.inflight)) {
    sync.inflight = null;
  } else {
    sync.inflight = null; // overtaken: its answer, a refusal or an ack, changes nothing here
    if (doc.loads === 0 || !sameJson(engine, doc.history.present)) {
      if (sync.timer) clearTimeout(sync.timer);
      sync.timer = null;
      sync.lastSent = null;
      doc.load(engine);
    }
  }
  pump();
}

/** Send the present arrangement when edits have settled, none is in flight, and the engine does not
 * hold it. */
function pump(): void {
  const engine = asArrangement(sync.store?.getState().arrangement);
  if (!engine || !sync.sender || sync.base === null || sync.inflight || sync.timer) return;
  const present = useDoc.getState().history.present;
  if (sameJson(present, engine)) return;
  if (sync.lastSent && sameJson(present, sync.lastSent)) return;
  sync.inflight = present;
  sync.lastSent = present;
  void sync.sender.ask({ type: "arrange", arrangement: fileForm(present), base: sync.base }).then((took) => {
    useArrangeSyncState.setState({ refused: !took });
    if (sync.inflight === present && !took) sync.inflight = null;
    pump();
  });
}

/** An edit: send once edits settle. */
function edited(): void {
  if (sync.timer) clearTimeout(sync.timer);
  sync.timer = setTimeout(() => {
    sync.timer = null;
    pump();
  }, SETTLE_MS);
}

/** Use the sync from one panel; returns the release. */
function attach(store: WireStore, sender: Sender): () => void {
  if (sync.store !== store) {
    sync.off?.();
    sync.off = null;
    sync.users = 0;
    reset(store, sender);
  }
  sync.sender = sender;
  if (sync.users++ === 0) {
    const offWire = store.subscribe(reconcile);
    const offDoc = useDoc.subscribe((s, prev) => {
      if (s.history.present !== prev.history.present) edited();
    });
    sync.off = () => {
      offWire();
      offDoc();
    };
  }
  reconcile();
  return () => {
    if (sync.store === store && --sync.users === 0) {
      sync.off?.();
      sync.off = null;
    }
  };
}

/**
 * Keeps the editor's arrangement and the engine's together while a panel shows the editor (the module
 * comment). Each present arrangement the engine does not hold goes to it SETTLE_MS after the last edit,
 * one at a time. Returns whether the engine refused the last one sent (its refusal, with the issues, is
 * the store's `arrange` refusal).
 */
export function useArrangeSync(): { readonly refused: boolean } {
  const { store, sender } = useWireContext();
  useEffect(() => attach(store, sender), [store, sender]);
  return { refused: useArrangeSyncState((s) => s.refused) };
}

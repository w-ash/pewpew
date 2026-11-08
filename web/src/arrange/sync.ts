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
  /** Set when the engine's arrangement changed elsewhere and replaced edits the engine had not taken. */
  readonly notice: string | null;
}

export const useArrangeSyncState = create<SyncState>()(() => ({ refused: false, notice: null }));

/** What the editor says when the engine's arrangement replaced edits it had not taken. */
export const CHANGED_ELSEWHERE = "The layout changed elsewhere; your unsaved edit was not applied.";

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
  /** Whether the connection was up at the last read. */
  connected: false,
  /** The digest of the engine's arrangement the history builds on: the `base` of the next `arrange`. */
  base: null as string | null,
  /** The engine's arrangement at `base`: the history holds edits it has not taken while its present differs. */
  known: null as Arrangement | null,
  /** Sent and not yet echoed or answered: one `arrange` at a time, so each names the base it edited. */
  inflight: null as Arrangement | null,
  /** The arrangement that was in flight when the connection closed: the engine may have applied it, and
   * an engine arrangement equal to it on reconnect is its echo. Cleared by the next arrangement read. */
  lost: null as Arrangement | null,
  /** Set when the engine's arrangement replaced the history since the last send: the edit sent no longer
   * exists, so a refusal of it has nothing left to show. */
  replaced: false,
  /** Set by a refusal, so the refused arrangement is not sent again by itself; an edit, an undo, a redo
   * or `retryArrange` clears it. */
  paused: false,
  timer: null as ReturnType<typeof setTimeout> | null,
};

function reset(store: WireStore, sender: Sender): void {
  if (sync.timer) clearTimeout(sync.timer);
  Object.assign(sync, {
    store, sender, seen: null, connected: false, base: null, known: null, inflight: null, lost: null, replaced: false, paused: false, timer: null,
  });
  useArrangeSyncState.setState({ refused: false, notice: null });
}

/** The count of the store's last `arrange` refusal; 0 for none. */
function refusalSeq(store: WireStore): number {
  return store.getState().refusals.arrange?.seq ?? 0;
}

/** Replace the history with the engine's `engine`, as nothing waits to be sent. */
function load(engine: Arrangement): void {
  if (sync.timer) clearTimeout(sync.timer);
  sync.timer = null;
  sync.paused = false;
  useDoc.getState().load(engine);
}

/**
 * Read the engine's arrangement when it is new, and while the connection is down hold the editor
 * read-only, so no edit is taken that cannot be sent. The engine's arrangement keeps the history when
 * it is the arrangement in flight (its echo), the present one, or the file the history builds on (the
 * same `base`, as after a reconnect: the present then goes again). Any other is a file changed elsewhere
 * (a save, a rebind, another tab) and replaces the history, whose undo steps were built on a file that
 * is gone; when the history held edits the engine had not taken, the notice says they were not applied.
 */
function reconcile(): void {
  const state = sync.store?.getState();
  if (!state) return;
  const doc = useDoc.getState();
  const editable = state.connected && state.arrangement !== null;
  if (doc.readOnly === editable) doc.setReadOnly(!editable);
  const reconnected = state.connected !== sync.connected;
  sync.connected = state.connected;
  if (state.arrangement === sync.seen) {
    if (reconnected) pump();
    return;
  }
  sync.seen = state.arrangement;
  const engine = asArrangement(state.arrangement);
  if (!engine || state.arrangementBase === null) return;
  const present = doc.history.present;
  const lost = sync.lost;
  sync.lost = null;
  if (sync.inflight && sameJson(engine, sync.inflight)) sync.inflight = null;
  else if (lost && sameJson(engine, lost)) {
    // The engine took the edit the closed connection left unanswered: its echo, so the history stays.
  } else if (doc.loads === 0) load(engine);
  else if (!sameJson(engine, present) && state.arrangementBase !== sync.base) {
    const unsent = sync.known !== null && !sameJson(present, sync.known);
    sync.replaced = true;
    load(engine);
    useArrangeSyncState.setState({ refused: false, notice: unsent ? CHANGED_ELSEWHERE : null });
  }
  sync.base = state.arrangementBase;
  sync.known = engine;
  pump();
}

/** Send the present arrangement when the connection is up, edits have settled, none is in flight, no
 * refusal holds it back, and the engine does not hold it. */
function pump(): void {
  const store = sync.store;
  const state = store?.getState();
  if (!store || !state?.connected || !sync.sender || sync.base === null) return;
  if (sync.inflight || sync.timer || sync.paused) return;
  const engine = asArrangement(state.arrangement);
  const present = useDoc.getState().history.present;
  if (!engine || sameJson(present, engine)) return;
  const sent = present;
  const seq = refusalSeq(store);
  sync.inflight = sent;
  sync.replaced = false;
  void sync.sender.ask({ type: "arrange", arrangement: fileForm(sent), base: sync.base }).then((took) => {
    // An ask settles untaken with no refusal when the connection closed: the engine may hold it or not,
    // and its next arrangement says which.
    // A refusal that carried the engine's arrangement was answered by loading it, whose notice says so.
    const refused = !took && sync.store === store && refusalSeq(store) !== seq && !sync.replaced;
    const closed = !took && sync.store === store && refusalSeq(store) === seq;
    if (took || refused) useArrangeSyncState.setState({ refused });
    if (sync.inflight !== sent) return;
    if (refused) sync.paused = true;
    if (closed) sync.lost = sent;
    // Taken: wait for its echo, which names the base the next edit builds on, unless it is already here.
    if (!took || sameJson(asArrangement(store.getState().arrangement), sent)) sync.inflight = null;
    pump();
  });
}

/** Send the present arrangement again after a refusal held it back (the engine was busy). */
export function retryArrange(): void {
  sync.paused = false;
  pump();
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
      if (s.history.present === prev.history.present) return;
      if (s.loads === prev.loads) {
        // An edit, an undo or a redo: what a refusal held back may go, and the notice is old news.
        sync.paused = false;
        if (useArrangeSyncState.getState().notice) useArrangeSyncState.setState({ notice: null });
      }
      edited();
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
 * the store's `arrange` refusal) and the notice of edits an arrangement from elsewhere replaced.
 */
export function useArrangeSync(): SyncState {
  const { store, sender } = useWireContext();
  useEffect(() => attach(store, sender), [store, sender]);
  return useArrangeSyncState();
}

import { create } from "zustand";
import type { Arrangement } from "./types";
import type { Selection } from "./arrangement";
import { commit, createHistory, type History, redo, undo } from "./history";

/** An arrangement with nothing in it, which the editor holds until it loads one. */
export const EMPTY_ARRANGEMENT: Arrangement = { format: "pewpew.arrangement", version: 1, fixtures: [], groups: [] };

interface DocState {
  history: History<Arrangement>;
  selection: Selection | null;
  /** While true, an edit, undo or redo changes nothing (a document that is still loading). */
  readOnly: boolean;
  /** Counts loads, so a reader can tell a load from an edit. */
  loads: number;
  commit: (next: Arrangement, coalesceKey?: string) => void;
  undo: () => void;
  redo: () => void;
  /** Replace the document and clear undo, as opening a file or the engine's own does. */
  load: (arrangement: Arrangement) => void;
  setReadOnly: (readOnly: boolean) => void;
  select: (selection: Selection | null) => void;
}

/** The arrangement the editor holds: its undo history (browser-side only) and what is selected. */
export const useDoc = create<DocState>()((set) => {
  const edit = (step: (h: History<Arrangement>) => History<Arrangement>) =>
    set((s) => (s.readOnly ? s : { history: step(s.history) }));
  return {
    history: createHistory(EMPTY_ARRANGEMENT),
    selection: null,
    readOnly: false,
    loads: 0,
    commit: (next, coalesceKey) => edit((h) => commit(h, next, coalesceKey ?? null, Date.now())),
    undo: () => edit(undo),
    redo: () => edit(redo),
    load: (arrangement) => set((s) => ({ history: createHistory(arrangement), selection: null, loads: s.loads + 1 })),
    setReadOnly: (readOnly) => set({ readOnly }),
    select: (selection) => set({ selection }),
  };
});

/** The document as the arrangement panel takes it (`ArrangementPanelProps`): the present arrangement,
 * the selection, undo and redo, and the edits. */
export function useDocEditor() {
  return {
    arrangement: useDoc((s) => s.history.present),
    onCommit: useDoc((s) => s.commit),
    selection: useDoc((s) => s.selection),
    onSelect: useDoc((s) => s.select),
    canUndo: useDoc((s) => s.history.past.length > 0),
    canRedo: useDoc((s) => s.history.future.length > 0),
    onUndo: useDoc((s) => s.undo),
    onRedo: useDoc((s) => s.redo),
  };
}

import { create } from "zustand";
import type { Arrangement } from "../api/types";
import { asArrangement, type Selection } from "../editor/arrangement";
import {
  commit,
  createHistory,
  type History,
  redo,
  undo,
} from "../editor/history";
import goldenRings from "../../../../src/pewpew/rig/examples/golden-rings.json";

/**
 * Where the open arrangement came from. A shared link opens read-only; the
 * first edit makes a fork, which is the visitor's own draft.
 */
export type Share =
  | { mode: "draft" }
  | { mode: "loading"; id: string }
  | { mode: "shared"; id: string }
  | { mode: "fork"; from: string };

/** The golden rings, from the rig package's examples. */
export const DEFAULT_ARRANGEMENT = asArrangement(goldenRings) as Arrangement;

interface DocState {
  history: History<Arrangement>;
  selection: Selection | null;
  share: Share;
  commit: (next: Arrangement, coalesceKey?: string) => void;
  undo: () => void;
  redo: () => void;
  /** Replace the document and clear undo, as opening a file or a link does. */
  load: (arrangement: Arrangement, share: Share) => void;
  setShare: (share: Share) => void;
  /** Record a save of `arrangement` as `id`. An edit made during the save forks the link. */
  markSaved: (arrangement: Arrangement, id: string) => void;
  select: (selection: Selection | null) => void;
}

function forked(share: Share): Share {
  return share.mode === "shared" ? { mode: "fork", from: share.id } : share;
}

/**
 * The state after an edit, undo or redo gives `history`. Moving off a shared
 * arrangement forks it. Nothing changes while a shared link loads, because
 * `load` replaces the document when it arrives.
 */
function moved(s: DocState, history: History<Arrangement>): Partial<DocState> {
  if (s.share.mode === "loading" || history === s.history) return s;
  return { history, share: forked(s.share) };
}

export const useDoc = create<DocState>()((set) => ({
  history: createHistory(DEFAULT_ARRANGEMENT),
  selection: null,
  share: { mode: "draft" },
  commit: (next, coalesceKey) =>
    set((s) =>
      moved(s, commit(s.history, next, coalesceKey ?? null, Date.now())),
    ),
  undo: () => set((s) => moved(s, undo(s.history))),
  redo: () => set((s) => moved(s, redo(s.history))),
  load: (arrangement, share) =>
    set({ history: createHistory(arrangement), selection: null, share }),
  setShare: (share) => set({ share }),
  markSaved: (arrangement, id) =>
    set((s) => ({
      share:
        s.history.present === arrangement
          ? { mode: "shared", id }
          : { mode: "fork", from: id },
    })),
  select: (selection) => set({ selection }),
}));

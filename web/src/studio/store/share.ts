import { create } from "zustand";
import type { Arrangement } from "../api/types";
import { asArrangement } from "../../arrange/arrangement";
import { useDoc } from "../../arrange/doc";
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

/** The golden rings, from the rig package's examples: the studio's first document. */
export const DEFAULT_ARRANGEMENT = asArrangement(goldenRings) as Arrangement;

interface ShareState {
  share: Share;
  setShare: (share: Share) => void;
  /** Open `arrangement` as `share`, clearing undo. */
  load: (arrangement: Arrangement, share: Share) => void;
  /** Record a save of `arrangement` as `id`. An edit made during the save forks the link. */
  markSaved: (arrangement: Arrangement, id: string) => void;
}

export const useShare = create<ShareState>()((set) => ({
  share: { mode: "draft" },
  setShare: (share) => {
    useDoc.getState().setReadOnly(share.mode === "loading");
    set({ share });
  },
  load: (arrangement, share) => {
    useShare.getState().setShare(share);
    useDoc.getState().load(arrangement);
  },
  markSaved: (arrangement, id) =>
    set({ share: useDoc.getState().history.present === arrangement ? { mode: "shared", id } : { mode: "fork", from: id } }),
}));

// Moving off a shared arrangement (an edit, undo or redo, not a load) forks it.
useDoc.subscribe((s, prev) => {
  const { share } = useShare.getState();
  if (s.history !== prev.history && s.loads === prev.loads && share.mode === "shared") {
    useShare.setState({ share: { mode: "fork", from: share.id } });
  }
});

if (useDoc.getState().loads === 0) useDoc.getState().load(DEFAULT_ARRANGEMENT);

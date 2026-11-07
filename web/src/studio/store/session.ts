import { create } from "zustand";

/** What the studio's own messages say; the wire's states are in the session's `WireStore`. */
export interface SessionState {
  /** Pixel count of the rig the server last bound; null until the first `bound`. */
  boundN: number | null;
  /** The streamed frame's estimated draw, under the power cap. */
  watts: number | null;
  /** The same frame's estimated draw without the cap. */
  uncappedWatts: number | null;
  t: number | null;
  /** Bound and visible, but no frame for `STALL_MS`: the server paused an idle session. */
  stalled: boolean;
}

export const initialSession: SessionState = {
  boundN: null,
  watts: null,
  uncappedWatts: null,
  t: null,
  stalled: false,
};

export const useSession = create<SessionState>()(() => initialSession);

import { create } from "zustand";
import type { Issue, ParamSpec, ParamValue } from "@/api/types";

export type Connection = "connecting" | "open" | "closed";

export interface SessionState {
  connection: Connection;
  /** Pixel count of the rig the server last bound; null until the first `bound`. */
  boundN: number | null;
  catalogDigest: string | null;
  boundIssues: Issue[];
  fps: number;
  patterns: string[];
  pattern: string;
  params: ParamSpec[];
  /** The values the engine holds, in their JSON form, from `hello` and each `params` echo. */
  accepted: Record<string, ParamValue>;
  /** Bumped on each refused `set` of a param, so its control snaps back. */
  refusedAt: Record<string, number>;
  engineError: string | null;
  refusal: { reason: string; issues: Issue[]; at: number } | null;
  /** The streamed frame's estimated draw, under the power cap. */
  watts: number | null;
  /** The same frame's estimated draw without the cap. */
  uncappedWatts: number | null;
  t: number | null;
  /** Bound and visible, but no frame for `STALL_MS`: the server paused an idle session. */
  stalled: boolean;
}

export const initialSession: SessionState = {
  connection: "connecting",
  boundN: null,
  catalogDigest: null,
  boundIssues: [],
  fps: 30,
  patterns: [],
  pattern: "",
  params: [],
  accepted: {},
  refusedAt: {},
  engineError: null,
  refusal: null,
  watts: null,
  uncappedWatts: null,
  t: null,
  stalled: false,
};

export const useSession = create<SessionState>()(() => initialSession);

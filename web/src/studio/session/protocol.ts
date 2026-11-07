/**
 * The studio's own messages on `/ws/session` (docs/studio/contracts.md,
 * "WebSocket"). Everything else on the socket is the control page's wire
 * (`src/wire/protocol.ts`): its requests, its states and its binary frames, a
 * `<fI` header (engine `t` as float32, uint32 sequence, little-endian) and
 * then n×3 display-ready RGB bytes in rig pixel order.
 */
import type { TypedMessage } from "../../wire/protocol";
import type { Arrangement } from "../api/types";

/** The gamma the session's frames are encoded with (`DISPLAY_GAMMA`, src/pewpew/sinks/base.py). */
export const DISPLAY_GAMMA = 2.2;

const FRAME_HEADER_BYTES = 8;

/** What the studio sends besides the wire's requests. */
export type StudioMessage =
  | { type: "bind"; arrangement: Arrangement }
  | { type: "pause" }
  | { type: "resume" };

/** What the studio reads besides the wire's states: the rig bound, with its pixel count, and the
 * streamed frame's estimated draw. */
export type StudioServerMessage =
  | { type: "bound"; n: number }
  | { type: "power"; watts: number; uncapped_watts: number };

const isNum = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);

/** The types the studio reads itself. Its `hello` is not the engine's (it has
 * no map and no gamma), and it needs nothing read: it comes on connect, which
 * opens the wire's state, and after each bind, which the per-frame states
 * follow again as they are. */
export const STUDIO_TYPES = ["hello", "bound", "power"] as const;

/** A studio message; null for a malformed one, and for a `hello`. */
export function parseStudioMessage(
  msg: TypedMessage,
): StudioServerMessage | null {
  switch (msg.type) {
    case "bound":
      return isNum(msg.n) ? { type: "bound", n: msg.n } : null;
    case "power":
      if (!isNum(msg.watts)) return null;
      return {
        type: "power",
        watts: msg.watts,
        // A server without the power cap sends one reading, uncapped.
        uncapped_watts: isNum(msg.uncapped_watts)
          ? msg.uncapped_watts
          : msg.watts,
      };
    default:
      return null;
  }
}

/** Build a frame, for the mock and tests. */
export function encodeFrame(
  t: number,
  seq: number,
  rgb: Uint8Array,
): ArrayBuffer {
  const buffer = new ArrayBuffer(FRAME_HEADER_BYTES + rgb.length);
  const view = new DataView(buffer);
  view.setFloat32(0, t, true);
  view.setUint32(4, seq >>> 0, true);
  new Uint8Array(buffer, FRAME_HEADER_BYTES).set(rgb);
  return buffer;
}

/** The session URL for a page location: `wss://` over https, `ws://` otherwise. */
export function sessionUrl(loc: Pick<Location, "protocol" | "host">): string {
  const scheme = loc.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${loc.host}/ws/session`;
}

/**
 * The studio's own messages on `/ws/session` (docs/studio/contracts.md,
 * "WebSocket"). Everything else on the socket is the control page's wire
 * (`src/wire/protocol.ts`): its requests, its states and its binary frames, a
 * `<fI` header (engine `t` as float32, uint32 sequence, little-endian) and
 * then n×3 display-ready RGB bytes in rig pixel order.
 */
import type { TypedMessage } from "../../wire/protocol";
import type { Arrangement } from "../api/types";

const FRAME_HEADER_BYTES = 8;

/** What the studio sends besides the wire's requests. */
export type StudioMessage =
  | { type: "bind"; arrangement: Arrangement }
  | { type: "pause" }
  | { type: "resume" };

/** What the studio reads besides the wire's states: the streamed frame's estimated draw. The bound
 * rig's pixel count is the wire's map, which a `layout` replaces. */
export type StudioServerMessage = {
  type: "power";
  watts: number;
  uncapped_watts: number;
};

const isNum = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);

/** The types the studio reads itself, the wire not having them yet. */
export const STUDIO_TYPES = ["power"] as const;

/** A studio message; null for a malformed one. */
export function parseStudioMessage(
  msg: TypedMessage,
): StudioServerMessage | null {
  switch (msg.type) {
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

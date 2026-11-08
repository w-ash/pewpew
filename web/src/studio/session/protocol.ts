/**
 * The studio's own requests on `/ws/session` (docs/studio/contracts.md,
 * "WebSocket"). Everything else on the socket is the control page's wire
 * (`src/wire/protocol.ts`): its requests, its states and its binary frames.
 */
import type { Arrangement } from "../api/types";

/** What the studio sends besides the wire's requests. */
export type StudioMessage =
  | { type: "bind"; arrangement: Arrangement }
  | { type: "pause" }
  | { type: "resume" };

/** The session URL for a page location: `wss://` over https, `ws://` otherwise. */
export function sessionUrl(loc: Pick<Location, "protocol" | "host">): string {
  const scheme = loc.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${loc.host}/ws/session`;
}

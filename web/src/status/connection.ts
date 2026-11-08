import { onEngineHost } from "../design/engineHost";
import { useWire, type WireState } from "../wire/store";

/** The connection: "waiting" before the first hello, "lost" after one. */
export type Link = "up" | "waiting" | "lost";

export function linkOf(s: Pick<WireState, "connected" | "session">): Link {
  return s.connected ? "up" : s.session ? "lost" : "waiting";
}

/** Where the words go: the top bar's chip, the control page's stage, or the studio's status line. */
export type Place = "chip" | "stage" | "status";

/** What `place` says of a connection that is not up, else null. Lost on the stage, on the laptop pewpew runs on,
 * means pewpew stopped, and once it has been `long`, what to do; elsewhere, maybe this device left the private
 * Wi-Fi. */
export function connectionText(link: Link, place: Place, long = false): string | null {
  switch (link) {
    case "up":
      return null;
    case "waiting":
      return place === "stage" ? `Waiting for the pewpew laptop at ${location.host}. Is pewpew running with --preview?` : "connecting…";
    case "lost":
      if (place === "chip") return "offline";
      if (place === "status") return "disconnected, retrying…";
      if (!onEngineHost()) return "Lost the pewpew laptop. Retrying… Is this device on the private Wi-Fi?";
      return `Lost pewpew. Retrying…${long ? " Stopped? Start the run again: this page reconnects on its own." : ""}`;
  }
}

/** The text for `place` while the wire is not connected, else null. */
export function useConnectionText(place: Place, long = false): string | null {
  return connectionText(useWire(linkOf), place, long);
}

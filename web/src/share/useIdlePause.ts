import { useEffect } from "react";
import { frameGap, STALE_MS } from "../health/health";
import { useWire, useWireContext } from "../wire/store";

const PRESSES = ["pointerdown", "keydown", "wheel"] as const;

/** While `on` (a Gallery session, capability "pause"): send `pause` as the tab hides, and as a hello comes
 * to a hidden tab, and `resume` as it shows, so a tab nobody sees costs the Gallery no frames. The session
 * also pauses itself after a while with no message; a press on the page while frames are stale then sends
 * `resume`, once a stale spell. */
export function useIdlePause(on: boolean): void {
  const { store, sender } = useWireContext();
  const session = useWire((s) => s.session);
  useEffect(() => {
    if (!on) return;
    // Frames are stale counted from the last one, else from the hello.
    const since = performance.now();
    let resumedAt = -Infinity;
    if (document.hidden) sender.send({ type: "pause" });
    const shown = () => {
      resumedAt = performance.now();
      sender.send({ type: document.hidden ? "pause" : "resume" });
    };
    const pressed = () => {
      const now = performance.now();
      if (!frameGap(now, store.lastFrameAt || since) || now - resumedAt < STALE_MS) return;
      resumedAt = now;
      sender.send({ type: "resume" });
    };
    document.addEventListener("visibilitychange", shown);
    for (const type of PRESSES) window.addEventListener(type, pressed, { capture: true, passive: true });
    return () => {
      document.removeEventListener("visibilitychange", shown);
      for (const type of PRESSES) window.removeEventListener(type, pressed, { capture: true });
    };
  }, [on, store, sender, session]);
}

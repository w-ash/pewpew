/**
 * One studio session over `/ws/session`, on the control page's socket and
 * wire store (`src/wire/`): the look editor sends its requests and
 * reads its states through them, and this client adds the studio's own.
 *
 * The server starts each session on a placeholder rig, so the client binds
 * as soon as the socket opens; the first `layout` after it gives the real
 * pixel count. A tab that is hidden sends `pause`, because Fly bills egress
 * (docs/studio/plan.md, "Share links").
 *
 * The server also pauses a session after 10 minutes with no message from the
 * client. When frames stop while the tab shows (or none follow a hello or
 * layout), the store's frame gap grows, and the next pointer or key press on the page sends `resume`.
 */
import { frameGap, STALE_MS } from "../../health/health";
import { Socket } from "../../wire/socket";
import { WireStore } from "../../wire/store";
import type { MapShape } from "../../room/layout";
import type { Arrangement } from "../api/types";
import { type StudioMessage, sessionUrl } from "./protocol";

export const BIND_DEBOUNCE_MS = 250;
const RETRY_MIN_MS = 1000;
const RETRY_MAX_MS = 10_000;
const ACTIVITY_EVENTS = ["pointerdown", "keydown", "wheel"] as const;

export interface SessionClientOptions {
  url?: string;
  WebSocket?: typeof WebSocket;
  visibility?: Pick<
    Document,
    "hidden" | "addEventListener" | "removeEventListener"
  >;
  /** Where a visitor's presses are heard; defaults to `window`. */
  activity?: Pick<EventTarget, "addEventListener" | "removeEventListener">;
  /** When a drag's held requests go out; the next animation frame by default. */
  requestFrame?: (cb: () => void) => void;
}

/** Whether two arrangements differ at most in `name`, which the engine never reads. */
function sameRig(a: Arrangement, b: Arrangement): boolean {
  return (
    JSON.stringify({ ...a, name: null }) ===
    JSON.stringify({ ...b, name: null })
  );
}

export class SessionClient {
  /** What the session's engine last said, as the look editor reads it. */
  readonly wire = new WireStore();
  /** The connection, and the editor's sender. */
  readonly socket: Socket<StudioMessage>;
  private retryMs = RETRY_MIN_MS;
  private bindTimer: ReturnType<typeof setTimeout> | null = null;
  private arrangement: Arrangement | null = null;
  private resumedAt = 0;
  private stopWire: (() => void) | null = null;
  /** The wire's connection count and map as last seen, to tell a `layout` from a `hello`. */
  private seenSession = 0;
  private seenMap: MapShape | null = null;
  private readonly visibility: SessionClientOptions["visibility"];
  private readonly activity: SessionClientOptions["activity"];

  constructor(opts: SessionClientOptions = {}) {
    this.visibility =
      opts.visibility ??
      (typeof document === "undefined" ? undefined : document);
    this.activity =
      opts.activity ?? (typeof window === "undefined" ? undefined : window);
    this.socket = new Socket<StudioMessage>(this.wire, {
      url: opts.url ?? sessionUrl(window.location),
      WebSocket: opts.WebSocket,
      requestFrame: opts.requestFrame,
      // The studio is built apart from its server: no build stamp to compare.
      build: null,
      onOpen: this.onOpen,
      reconnectMs: () => {
        const wait = this.retryMs;
        this.retryMs = Math.min(this.retryMs * 2, RETRY_MAX_MS);
        return wait;
      },
    });
  }

  start() {
    this.visibility?.addEventListener("visibilitychange", this.onVisibility);
    for (const type of ACTIVITY_EVENTS)
      this.activity?.addEventListener(type, this.onActivity, { passive: true });
    this.stopWire = this.wire.subscribe(this.onWireState);
    this.socket.start();
  }

  stop() {
    this.visibility?.removeEventListener("visibilitychange", this.onVisibility);
    for (const type of ACTIVITY_EVENTS)
      this.activity?.removeEventListener(type, this.onActivity);
    if (this.bindTimer) clearTimeout(this.bindTimer);
    this.stopWire?.();
    this.socket.stop();
  }

  /**
   * Bind `arrangement` after a short quiet spell; the latest call wins. A
   * change of name alone sends nothing.
   */
  bind(arrangement: Arrangement) {
    const previous = this.arrangement;
    this.arrangement = arrangement;
    if (previous && sameRig(previous, arrangement)) return;
    if (this.bindTimer) clearTimeout(this.bindTimer);
    this.bindTimer = setTimeout(() => {
      this.bindTimer = null;
      this.sendBind();
    }, BIND_DEBOUNCE_MS);
  }

  private sendBind() {
    if (this.arrangement)
      this.socket.send({ type: "bind", arrangement: this.arrangement });
  }

  private onOpen = () => {
    if (this.bindTimer) {
      clearTimeout(this.bindTimer);
      this.bindTimer = null;
    }
    this.sendBind();
    if (this.visibility?.hidden) this.socket.send({ type: "pause" });
  };

  private onVisibility = () => {
    this.resumedAt = performance.now();
    this.socket.send({ type: this.visibility?.hidden ? "pause" : "resume" });
  };

  /** A press while frames are stale asks the server to resume, at most once per stale spell. */
  private onActivity = () => {
    const now = performance.now();
    if (!frameGap(now, this.wire.heardAt()) || now - this.resumedAt < STALE_MS) return;
    this.resumedAt = now;
    this.socket.send({ type: "resume" });
  };

  /** The first `layout` of a connection is the bound rig. A `hello` is the placeholder. */
  private onWireState = () => {
    const { session, map } = this.wire.getState();
    const layout = session === this.seenSession && map !== this.seenMap && map !== null;
    this.seenSession = session;
    this.seenMap = map;
    // Backoff resets only once a bind works, so a session that dies on
    // every bind retries ever more slowly instead of once a second.
    if (layout) this.retryMs = RETRY_MIN_MS;
  };
}

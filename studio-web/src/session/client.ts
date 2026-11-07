/**
 * One studio session over `/ws/session`, on the control page's socket and
 * wire store (`@pewpew/page/wire`): the look editor sends its requests and
 * reads its states through them, and this client adds the studio's own.
 *
 * The server starts each session on a placeholder rig, so the client binds
 * as soon as the socket opens and drops frames until `bound` gives the real
 * pixel count. A tab that is hidden sends `pause`, because Fly bills egress
 * (docs/studio/plan.md, "Share links").
 *
 * The server also pauses a session after 10 minutes with no message from the
 * client. When frames stop while the tab shows, the store's `stalled` turns
 * true, and the next pointer or key press on the page sends `resume`.
 */
import { type Frame, Socket, WireStore } from "@pewpew/page/wire";
import type { Arrangement } from "@/api/types";
import { type SessionState, useSession } from "@/store/session";
import { frameBus } from "@/viewer/frameBus";
import {
  DISPLAY_GAMMA,
  parseStudioMessage,
  STUDIO_TYPES,
  type StudioMessage,
  type StudioServerMessage,
  sessionUrl,
} from "./protocol";

export const BIND_DEBOUNCE_MS = 250;
const RETRY_MIN_MS = 1000;
const RETRY_MAX_MS = 10_000;
const T_REPORT_MS = 250;
/** No frame for this long, on a bound and visible session, counts as stalled. */
export const STALL_MS = 2000;
const ACTIVITY_EVENTS = ["pointerdown", "keydown", "wheel"] as const;

export interface SessionClientOptions {
  url?: string;
  WebSocket?: typeof WebSocket;
  /** Defaults to the zustand session store. */
  store?: {
    getState: () => SessionState;
    setState: (patch: Partial<SessionState>) => void;
  };
  visibility?: Pick<
    Document,
    "hidden" | "addEventListener" | "removeEventListener"
  >;
  /** Where a visitor's presses are heard; defaults to `window`. */
  activity?: Pick<EventTarget, "addEventListener" | "removeEventListener">;
  onFrame?: (frame: Frame) => void;
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
  private lastTReport = 0;
  private lastFrameAt = 0;
  private stallTimer: ReturnType<typeof setInterval> | null = null;
  private stopFrames: (() => void) | null = null;
  private readonly store: NonNullable<SessionClientOptions["store"]>;
  private readonly visibility: SessionClientOptions["visibility"];
  private readonly activity: SessionClientOptions["activity"];
  private readonly onFrame: (frame: Frame) => void;

  constructor(opts: SessionClientOptions = {}) {
    this.store = opts.store ?? useSession;
    this.visibility =
      opts.visibility ??
      (typeof document === "undefined" ? undefined : document);
    this.activity =
      opts.activity ?? (typeof window === "undefined" ? undefined : window);
    this.onFrame = opts.onFrame ?? ((f) => frameBus.push(f));
    this.socket = new Socket<StudioMessage>(this.wire, {
      url: opts.url ?? sessionUrl(window.location),
      WebSocket: opts.WebSocket,
      requestFrame: opts.requestFrame,
      // The studio is built apart from its server: no build stamp to compare.
      build: null,
      onOpen: this.onOpen,
      ownTypes: STUDIO_TYPES,
      onOwnMessage: (typed) => {
        const msg = parseStudioMessage(typed);
        if (msg) this.handle(msg);
      },
      onClose: this.onClose,
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
    this.stallTimer = setInterval(this.checkStall, STALL_MS / 2);
    this.stopFrames = this.wire.subscribeFrame(this.onWireFrame);
    this.socket.start();
  }

  stop() {
    this.visibility?.removeEventListener("visibilitychange", this.onVisibility);
    for (const type of ACTIVITY_EVENTS)
      this.activity?.removeEventListener(type, this.onActivity);
    if (this.stallTimer) clearInterval(this.stallTimer);
    if (this.bindTimer) clearTimeout(this.bindTimer);
    this.stopFrames?.();
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
    // The server sends no engine hello: the connection opens the wire's state.
    this.wire.opened({ gamma: DISPLAY_GAMMA, map: null });
    if (this.bindTimer) {
      clearTimeout(this.bindTimer);
      this.bindTimer = null;
    }
    this.sendBind();
    if (this.visibility?.hidden) this.socket.send({ type: "pause" });
  };

  private onClose = () => {
    // The bound rig died with the session.
    this.store.setState({
      boundN: null,
      watts: null,
      uncappedWatts: null,
      stalled: false,
    });
  };

  private onVisibility = () => {
    this.lastFrameAt = performance.now();
    this.socket.send({ type: this.visibility?.hidden ? "pause" : "resume" });
  };

  private onActivity = () => {
    if (!this.store.getState().stalled) return;
    this.lastFrameAt = performance.now();
    this.socket.send({ type: "resume" });
  };

  private checkStall = () => {
    const live =
      this.wire.getState().connected &&
      this.store.getState().boundN !== null &&
      !this.visibility?.hidden;
    const stalled = live && performance.now() - this.lastFrameAt > STALL_MS;
    if (stalled !== this.store.getState().stalled)
      this.store.setState({ stalled });
  };

  /** A frame the wire received: shown only when it is as long as the bound rig. */
  private onWireFrame = () => {
    const frame = this.wire.getFrame();
    const n = this.store.getState().boundN;
    if (!frame || n === null || frame.rgb.length !== 3 * n) return;
    this.onFrame(frame);
    const now = performance.now();
    this.lastFrameAt = now;
    if (this.store.getState().stalled) this.store.setState({ stalled: false });
    if (now - this.lastTReport >= T_REPORT_MS) {
      this.lastTReport = now;
      this.store.setState({ t: frame.t });
    }
  };

  private handle(msg: StudioServerMessage) {
    switch (msg.type) {
      case "bound":
        // Backoff resets only once a bind works, so a session that dies on
        // every bind retries ever more slowly instead of once a second.
        this.retryMs = RETRY_MIN_MS;
        this.lastFrameAt = performance.now();
        this.store.setState({ boundN: msg.n });
        break;
      case "power":
        this.store.setState({
          watts: msg.watts,
          uncappedWatts: msg.uncapped_watts,
        });
        break;
    }
  }
}

/**
 * One studio session over `/ws/session`.
 *
 * The server starts each session on a placeholder rig and sends `hello`
 * before any bind, so the client binds as soon as the socket opens and drops
 * frames until `bound` gives the real pixel count. A tab that is hidden sends
 * `pause`, because Fly bills egress (docs/studio/plan.md, "Share links").
 *
 * The server also pauses a session after 10 minutes with no message from the
 * client. When frames stop while the tab shows, the store's `stalled` turns
 * true, and the next pointer or key press on the page sends `resume`.
 */
import type { Arrangement, ParamValue } from "@/api/types";
import { type SessionState, useSession } from "@/store/session";
import { frameBus } from "@/viewer/frameBus";
import {
  type ClientMessage,
  encodeClientMessage,
  type Frame,
  parseFrame,
  parseServerMessage,
  type ServerMessage,
  sessionUrl,
} from "./protocol";

export const BIND_DEBOUNCE_MS = 250;
const RETRY_MIN_MS = 1000;
const RETRY_MAX_MS = 10_000;
const T_REPORT_MS = 250;
/** No frame for this long, on a bound and visible session, counts as stalled. */
export const STALL_MS = 2000;
const ACTIVITY_EVENTS = ["pointerdown", "keydown", "wheel"] as const;

type SocketLike = Pick<WebSocket, "send" | "close" | "readyState"> & {
  binaryType: BinaryType;
  onopen: ((ev: Event) => void) | null;
  onclose: ((ev: CloseEvent) => void) | null;
  onmessage: ((ev: MessageEvent) => void) | null;
  onerror: ((ev: Event) => void) | null;
};

export interface SessionClientOptions {
  url?: string;
  createSocket?: (url: string) => SocketLike;
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
}

/** Whether two arrangements differ at most in `name`, which the engine never reads. */
function sameRig(a: Arrangement, b: Arrangement): boolean {
  return (
    JSON.stringify({ ...a, name: null }) ===
    JSON.stringify({ ...b, name: null })
  );
}

const OPEN = 1;

export class SessionClient {
  private socket: SocketLike | null = null;
  private retryMs = RETRY_MIN_MS;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private bindTimer: ReturnType<typeof setTimeout> | null = null;
  private arrangement: Arrangement | null = null;
  private chosenPattern: string | null = null;
  private lastTReport = 0;
  private lastFrameAt = 0;
  private stallTimer: ReturnType<typeof setInterval> | null = null;
  private stopped = false;
  private readonly url: string;
  private readonly createSocket: (url: string) => SocketLike;
  private readonly store: NonNullable<SessionClientOptions["store"]>;
  private readonly visibility: SessionClientOptions["visibility"];
  private readonly activity: SessionClientOptions["activity"];
  private readonly onFrame: (frame: Frame) => void;

  constructor(opts: SessionClientOptions = {}) {
    this.url = opts.url ?? sessionUrl(window.location);
    this.createSocket = opts.createSocket ?? ((u) => new WebSocket(u));
    this.store = opts.store ?? useSession;
    this.visibility =
      opts.visibility ??
      (typeof document === "undefined" ? undefined : document);
    this.activity =
      opts.activity ?? (typeof window === "undefined" ? undefined : window);
    this.onFrame = opts.onFrame ?? ((f) => frameBus.push(f));
  }

  start() {
    this.stopped = false;
    this.visibility?.addEventListener("visibilitychange", this.onVisibility);
    for (const type of ACTIVITY_EVENTS)
      this.activity?.addEventListener(type, this.onActivity, { passive: true });
    this.stallTimer = setInterval(this.checkStall, STALL_MS / 2);
    this.connect();
  }

  stop() {
    this.stopped = true;
    this.visibility?.removeEventListener("visibilitychange", this.onVisibility);
    for (const type of ACTIVITY_EVENTS)
      this.activity?.removeEventListener(type, this.onActivity);
    if (this.stallTimer) clearInterval(this.stallTimer);
    if (this.retryTimer) clearTimeout(this.retryTimer);
    if (this.bindTimer) clearTimeout(this.bindTimer);
    const s = this.socket;
    this.socket = null;
    s?.close();
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

  setPattern(name: string) {
    this.chosenPattern = name;
    this.send({ type: "pattern", name });
  }

  setParam(name: string, value: ParamValue) {
    this.send({ type: "set", name, value });
  }

  private sendBind() {
    if (this.arrangement)
      this.send({ type: "bind", arrangement: this.arrangement });
  }

  private send(msg: ClientMessage) {
    if (this.socket && this.socket.readyState === OPEN) {
      this.socket.send(encodeClientMessage(msg));
    }
  }

  private onVisibility = () => {
    this.lastFrameAt = performance.now();
    this.send({ type: this.visibility?.hidden ? "pause" : "resume" });
  };

  private onActivity = () => {
    if (!this.store.getState().stalled) return;
    this.lastFrameAt = performance.now();
    this.send({ type: "resume" });
  };

  private checkStall = () => {
    const live =
      this.socket?.readyState === OPEN &&
      this.store.getState().boundN !== null &&
      !this.visibility?.hidden;
    const stalled = live && performance.now() - this.lastFrameAt > STALL_MS;
    if (stalled !== this.store.getState().stalled)
      this.store.setState({ stalled });
  };

  private connect() {
    if (this.stopped) return;
    this.store.setState({ connection: "connecting" });
    const ws = this.createSocket(this.url);
    ws.binaryType = "arraybuffer";
    this.socket = ws;
    ws.onopen = () => {
      if (this.socket !== ws) return;
      this.store.setState({ connection: "open" });
      if (this.bindTimer) {
        clearTimeout(this.bindTimer);
        this.bindTimer = null;
      }
      this.sendBind();
      if (this.chosenPattern)
        this.send({ type: "pattern", name: this.chosenPattern });
      if (this.visibility?.hidden) this.send({ type: "pause" });
    };
    ws.onmessage = (ev) => {
      if (this.socket !== ws) return;
      if (typeof ev.data === "string") {
        const msg = parseServerMessage(ev.data);
        if (msg) this.handle(msg);
      } else if (ev.data instanceof ArrayBuffer) {
        this.handleFrame(ev.data);
      }
    };
    ws.onclose = () => {
      if (this.socket !== ws) return;
      this.socket = null;
      // The engine's error and the bound rig died with the session.
      this.store.setState({
        connection: "closed",
        boundN: null,
        engineError: null,
        watts: null,
        uncappedWatts: null,
        stalled: false,
      });
      if (this.stopped) return;
      this.retryTimer = setTimeout(() => this.connect(), this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, RETRY_MAX_MS);
    };
    ws.onerror = () => {};
  }

  private handleFrame(buffer: ArrayBuffer) {
    const n = this.store.getState().boundN;
    if (n === null) return;
    const frame = parseFrame(buffer, n);
    if (!frame) return;
    this.onFrame(frame);
    const now = performance.now();
    this.lastFrameAt = now;
    if (this.store.getState().stalled) this.store.setState({ stalled: false });
    if (now - this.lastTReport >= T_REPORT_MS) {
      this.lastTReport = now;
      this.store.setState({ t: frame.t });
    }
  }

  handle(msg: ServerMessage) {
    const set = (patch: Partial<SessionState>) => this.store.setState(patch);
    switch (msg.type) {
      case "hello":
        set({
          fps: msg.fps,
          patterns: msg.patterns,
          pattern: msg.pattern,
          params: msg.params,
          accepted: {
            ...Object.fromEntries(msg.params.map((p) => [p.name, p.default])),
            ...msg.values,
          } as Record<string, ParamValue>,
        });
        break;
      case "status":
        set({ engineError: msg.error });
        break;
      case "declare":
        set({ params: msg.params });
        break;
      case "params":
        set({ accepted: { ...this.store.getState().accepted, ...msg.values } });
        break;
      case "refused": {
        const state = this.store.getState();
        set({
          refusal: {
            reason: msg.reason,
            issues: msg.issues ?? [],
            at: Date.now(),
          },
          refusedAt:
            msg.control === "set" && msg.name
              ? { ...state.refusedAt, [msg.name]: Date.now() }
              : state.refusedAt,
        });
        break;
      }
      case "bound":
        // Backoff resets only once a bind works, so a session that dies on
        // every bind retries ever more slowly instead of once a second.
        this.retryMs = RETRY_MIN_MS;
        this.lastFrameAt = performance.now();
        set({
          boundN: msg.n,
          catalogDigest: msg.catalog_digest,
          boundIssues: msg.issues,
        });
        break;
      case "power":
        set({ watts: msg.watts, uncappedWatts: msg.uncapped_watts });
        break;
    }
  }
}

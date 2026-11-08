// A page's one connection to the engine. Engine restarts are routine, so a
// closed socket reconnects after a second; one that answers with another page
// build (an upgrade) reloads the tab, since this page cannot drive its wire.
// A page whose server reads more than the wire (the studio's `bind`) sends its own
// messages through the same connection.
import { asServerMessage, parseFrame, parseTyped, type ClientMessage, type RequestId, type Sender } from "./protocol";
import type { WireStore } from "./store";

export const RECONNECT_MS = 1000;

export interface SocketOptions {
  readonly url: string;
  readonly WebSocket?: typeof WebSocket;
  readonly requestFrame?: (cb: () => void) => void;
  readonly now?: () => number;
  /** This page's build stamp; by default its `pewpew-build` meta, or null outside a build. */
  readonly build?: string | null;
  readonly reload?: () => void;
  /** Called as each connection opens, before any message on it. */
  readonly onOpen?: () => void;
  /** The wait before a reconnect, asked at each close; RECONNECT_MS by default. */
  readonly reconnectMs?: () => number;
}

/** A message of a page's own, outside the wire's vocabulary. */
export interface OwnMessage {
  readonly type: string;
}

/** What a newer message replaces: a set of the same param, any master. */
function slot(msg: ClientMessage): string {
  return msg.type === "set" ? `set:${msg.name}` : msg.type;
}

/** The connection; `Own` is what else the page sends (none for the control page). */
export class Socket<Own extends OwnMessage = never> implements Sender {
  private ws: WebSocket | null = null;
  private stopped = false;
  private retry: ReturnType<typeof setTimeout> | null = null;
  /** Messages a drag produces, held to the next animation frame, the newest per slot. */
  private readonly pending = new Map<string, ClientMessage>();
  private flushing = false;
  /** Each request `ask` sent that the engine has not answered, by its id. */
  private readonly asked = new Map<RequestId, (took: boolean) => void>();
  private nextId = 1;
  private readonly WS: typeof WebSocket;
  private readonly requestFrame: (cb: () => void) => void;
  private readonly now: () => number;
  private readonly build: string | null;
  private readonly reload: () => void;
  private readonly store: WireStore;
  private readonly options: SocketOptions;

  constructor(store: WireStore, options: SocketOptions) {
    this.store = store;
    this.options = options;
    this.WS = options.WebSocket ?? WebSocket;
    this.requestFrame = options.requestFrame ?? ((cb) => requestAnimationFrame(cb));
    this.now = options.now ?? (() => performance.now());
    this.build = options.build !== undefined ? options.build
      : (document.querySelector<HTMLMetaElement>('meta[name="pewpew-build"]')?.content ?? null);
    this.reload = options.reload ?? (() => location.reload());
  }

  // A hidden tab runs no animation frames: what waits is sent as it hides.
  private readonly flushOnHide = () => this.flush();

  start(): void {
    this.stopped = false;
    const ws = new this.WS(this.options.url);
    this.ws = ws;
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      if (this.ws === ws) this.options.onOpen?.();
    };
    ws.onmessage = (ev: MessageEvent) => {
      if (this.ws !== ws) return;
      if (typeof ev.data === "string") {
        const msg = asServerMessage(parseTyped(ev.data));
        if (msg?.type === "hello" && this.build && msg.build && msg.build !== this.build) this.reload();
        else if (msg) {
          this.store.receive(msg);
          if ((msg.type === "ack" || msg.type === "refused") && msg.id !== null) this.answered(msg.id, msg.type === "ack");
        }
      } else if (ev.data instanceof ArrayBuffer) {
        this.store.receiveFrame(parseFrame(ev.data), this.now());
      }
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      this.pending.clear();
      for (const settle of this.asked.values()) settle(false);
      this.asked.clear();
      this.store.disconnected();
      if (!this.stopped) this.retry = setTimeout(() => this.start(), this.options.reconnectMs?.() ?? RECONNECT_MS);
    };
  }

  /** Close the connection for good: no reconnect follows. What it asked settles now, untaken: a `start`
   * before the close event comes opens a new connection, which answers none of it. */
  stop(): void {
    this.stopped = true;
    if (this.retry) clearTimeout(this.retry);
    this.ws?.close();
    for (const settle of this.asked.values()) settle(false);
    this.asked.clear();
  }

  /** Send now, after anything held, so the engine sees requests in the order made. */
  send(msg: ClientMessage | Own): void {
    this.flush();
    this.write(msg);
  }

  ask(msg: ClientMessage): Promise<boolean> {
    const id = this.nextId++;
    const answer = new Promise<boolean>((resolve) => this.asked.set(id, resolve));
    this.flush();
    if (!this.write(msg, id)) this.answered(id, false); // not sent, so nothing will answer it
    return answer;
  }

  private answered(id: RequestId, took: boolean): void {
    this.asked.get(id)?.(took);
    this.asked.delete(id);
  }

  sendLatest(msg: ClientMessage): void {
    // Deleted first, so the flush sends in the order of the latest requests.
    this.pending.delete(slot(msg));
    this.pending.set(slot(msg), msg);
    if (this.flushing) return;
    this.flushing = true;
    document.addEventListener("visibilitychange", this.flushOnHide);
    this.requestFrame(() => this.flush());
  }

  private flush(): void {
    this.flushing = false;
    document.removeEventListener("visibilitychange", this.flushOnHide);
    for (const msg of this.pending.values()) this.write(msg);
    this.pending.clear();
  }

  /** Send `msg`, with `id` when given, if the socket is open. Returns whether it went. */
  private write(msg: ClientMessage | Own, id?: RequestId): boolean {
    if (this.ws?.readyState !== this.WS.OPEN) return false;
    this.ws.send(JSON.stringify(id === undefined ? msg : { ...msg, id }));
    return true;
  }
}

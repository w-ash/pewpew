// The page's one connection to its server, the engine or the Gallery. Engine
// restarts are routine, so a socket closed after its hello reconnects within a
// second; one refused or closed before a hello (a full Gallery, an engine that
// is down) waits twice as long each time, to RECONNECT_MAX_MS. One that answers
// with another page build (an upgrade) reloads the tab, since this page cannot
// drive its wire.
import { asServerMessage, parseFrame, parseTyped, type ClientMessage, type RequestId, type Sender } from "./protocol";
import type { WireStore } from "./store";

export const RECONNECT_MS = 1000;
/** The longest wait before a reconnect. */
export const RECONNECT_MAX_MS = 10_000;

export interface SocketOptions {
  /** By default the page's own (`socketUrl`). */
  readonly url?: string;
  readonly WebSocket?: typeof WebSocket;
  readonly requestFrame?: (cb: () => void) => void;
  readonly now?: () => number;
  /** This page's build stamp; by default its `pewpew-build` meta, or null outside a build. */
  readonly build?: string | null;
  readonly reload?: () => void;
}

/** What a newer message replaces: a set of the same param, any master. */
function slot(msg: ClientMessage): string {
  return msg.type === "set" ? `set:${msg.name}` : msg.type;
}

/** The page's URL for the socket of the server at `loc`: the same host, by the page's scheme, with the page's
 * query, and on a share's page (`/a/<id>`) the share's id as `a`. */
export function socketUrl(loc: Pick<Location, "protocol" | "host" | "pathname" | "search">): string {
  const share = /^\/a\/([\w-]{22})$/.exec(loc.pathname)?.[1];
  // "http:" gives "ws:", "https:" "wss:".
  return `ws${loc.protocol.slice(4)}//${loc.host}/ws${loc.search}${share ? `${loc.search ? "&" : "?"}a=${share}` : ""}`;
}

/** The connection. */
export class Socket implements Sender {
  private ws: WebSocket | null = null;
  /** The last wait before a reconnect. */
  private wait = RECONNECT_MS / 2;
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

  constructor(store: WireStore, options: SocketOptions = {}) {
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
    const ws = new this.WS(this.options.url ?? socketUrl(location));
    this.ws = ws;
    ws.binaryType = "arraybuffer";
    ws.onmessage = (ev: MessageEvent) => {
      if (this.ws !== ws) return;
      if (typeof ev.data === "string") {
        const msg = asServerMessage(parseTyped(ev.data));
        if (msg?.type === "hello" && this.build && msg.build && msg.build !== this.build) this.reload();
        else if (msg) {
          this.store.receive(msg);
          // An ack, an exported or a refusal answers the request its `id` names.
          if ("id" in msg && msg.id !== null) this.answered(msg.id, msg.type !== "refused");
        }
      } else if (ev.data instanceof ArrayBuffer) {
        this.store.receiveFrame(parseFrame(ev.data), this.now());
      }
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      // RECONNECT_MS after a hello, else twice the last wait; each less up to half at random, so the pages a
      // full Gallery refused do not all come back at once.
      this.wait = Math.min(this.store.getState().connected ? RECONNECT_MS : this.wait * 2, RECONNECT_MAX_MS);
      this.ws = null;
      this.pending.clear();
      for (const settle of this.asked.values()) settle(false);
      this.asked.clear();
      this.store.disconnected();
      setTimeout(() => this.start(), this.wait * (1 - Math.random() / 2));
    };
  }

  /** Send now, after anything held, so the engine sees requests in the order made. */
  send(msg: ClientMessage): void {
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
  private write(msg: ClientMessage, id?: RequestId): boolean {
    if (this.ws?.readyState !== this.WS.OPEN) return false;
    this.ws.send(JSON.stringify(id === undefined ? msg : { ...msg, id }));
    return true;
  }
}

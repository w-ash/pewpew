// The page's one connection to the engine. Engine restarts are routine, so a
// closed socket reconnects after a second; one that answers with another page
// build (an upgrade) reloads the tab, since this page cannot drive its wire.
import { parseFrame, parseMessage, type ClientMessage, type RequestId, type Sender } from "./protocol";
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
}

/** What a newer message replaces: a set of the same param, any master. */
function slot(msg: ClientMessage): string {
  return msg.type === "set" ? `set:${msg.name}` : msg.type;
}

export class Socket implements Sender {
  private ws: WebSocket | null = null;
  /** Messages a drag produces, held to the next animation frame, the newest per slot. */
  private readonly pending = new Map<string, ClientMessage>();
  private flushing = false;
  /** Each request `ask` sent that the engine has not answered, by its id. */
  private readonly asked = new Map<RequestId, () => void>();
  private nextId = 1;
  private readonly WS: typeof WebSocket;
  private readonly requestFrame: (cb: () => void) => void;
  private readonly now: () => number;
  private readonly build: string | null;
  private readonly reload: () => void;

  constructor(private readonly store: WireStore, private readonly options: SocketOptions) {
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
    const ws = new this.WS(this.options.url);
    this.ws = ws;
    ws.binaryType = "arraybuffer";
    ws.onmessage = (ev: MessageEvent) => {
      if (typeof ev.data === "string") {
        const msg = parseMessage(ev.data);
        if (msg?.type === "hello" && this.build && msg.build && msg.build !== this.build) this.reload();
        else if (msg) {
          this.store.receive(msg);
          if ((msg.type === "ack" || msg.type === "refused") && msg.id !== null) this.answered(msg.id);
        }
      } else if (ev.data instanceof ArrayBuffer) {
        this.store.receiveFrame(parseFrame(ev.data), this.now());
      }
    };
    ws.onclose = () => {
      this.ws = null;
      this.pending.clear();
      for (const settle of this.asked.values()) settle();
      this.asked.clear();
      this.store.disconnected();
      setTimeout(() => this.start(), RECONNECT_MS);
    };
  }

  /** Send now, after anything held, so the engine sees requests in the order made. */
  send(msg: ClientMessage): void {
    this.flush();
    this.write(msg);
  }

  ask(msg: ClientMessage): Promise<void> {
    const id = this.nextId++;
    const answer = new Promise<void>((resolve) => this.asked.set(id, resolve));
    this.flush();
    if (!this.write(msg, id)) this.answered(id); // not sent, so nothing will answer it
    return answer;
  }

  private answered(id: RequestId): void {
    this.asked.get(id)?.();
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

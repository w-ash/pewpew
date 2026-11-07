import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_ARRANGEMENT } from "@/store/doc";
import { initialSession, type SessionState } from "@/store/session";
import { BIND_DEBOUNCE_MS, SessionClient, STALL_MS } from "./client";
import { encodeFrame, type Frame } from "./protocol";

class FakeSocket {
  static all: FakeSocket[] = [];
  readyState = 0;
  binaryType: BinaryType = "blob";
  sent: string[] = [];
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  url: string;
  constructor(url: string) {
    this.url = url;
    FakeSocket.all.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = 3;
    this.onclose?.({} as CloseEvent);
  }
  open() {
    this.readyState = 1;
    this.onopen?.({} as Event);
  }
  receive(data: string | ArrayBuffer) {
    this.onmessage?.({ data } as MessageEvent);
  }
  types() {
    return this.sent.map((s) => JSON.parse(s).type);
  }
}

function harness(hidden = false) {
  let state: SessionState = { ...initialSession };
  const store = {
    getState: () => state,
    setState: (patch: Partial<SessionState>) => {
      state = { ...state, ...patch };
    },
  };
  const listeners = new Set<() => void>();
  const visibility = {
    hidden,
    addEventListener: (_: string, fn: () => void) => listeners.add(fn),
    removeEventListener: (_: string, fn: () => void) => listeners.delete(fn),
  } as unknown as Document;
  const frames: Frame[] = [];
  const activity = new EventTarget();
  const client = new SessionClient({
    url: "ws://test/ws/session",
    createSocket: (url) => new FakeSocket(url) as unknown as WebSocket,
    store,
    visibility,
    activity,
    onFrame: (f) => frames.push(f),
  });
  const setHidden = (h: boolean) => {
    (visibility as { hidden: boolean }).hidden = h;
    for (const fn of listeners) fn();
  };
  return {
    client,
    store,
    frames,
    setHidden,
    press: () => activity.dispatchEvent(new Event("pointerdown")),
    socket: () => FakeSocket.all[FakeSocket.all.length - 1],
  };
}

const hello = (n: number) =>
  JSON.stringify({
    type: "hello",
    n,
    fps: 30,
    patterns: ["rainbow"],
    pattern: "rainbow",
    params: [],
  });

describe("SessionClient", () => {
  beforeEach(() => {
    FakeSocket.all = [];
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  it("binds as soon as the socket opens", () => {
    const h = harness();
    h.client.bind(DEFAULT_ARRANGEMENT);
    h.client.start();
    h.socket().open();
    expect(h.socket().types()).toEqual(["bind"]);
    expect(JSON.parse(h.socket().sent[0]).arrangement).toEqual(
      DEFAULT_ARRANGEMENT,
    );
  });

  it("debounces binds and sends only the latest", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.client.bind({ ...DEFAULT_ARRANGEMENT, name: "one" });
    h.client.bind({ ...DEFAULT_ARRANGEMENT, name: "two" });
    vi.advanceTimersByTime(BIND_DEBOUNCE_MS - 1);
    expect(h.socket().sent).toEqual([]);
    vi.advanceTimersByTime(1);
    expect(h.socket().sent.map((s) => JSON.parse(s).arrangement.name)).toEqual([
      "two",
    ]);
  });

  it("sends no bind for a change of name alone", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.client.bind(DEFAULT_ARRANGEMENT);
    vi.advanceTimersByTime(BIND_DEBOUNCE_MS);
    h.client.bind({ ...DEFAULT_ARRANGEMENT, name: "renamed" });
    vi.advanceTimersByTime(BIND_DEBOUNCE_MS);
    expect(h.socket().types()).toEqual(["bind"]);
    h.client.bind({ ...DEFAULT_ARRANGEMENT, groups: [] });
    vi.advanceTimersByTime(BIND_DEBOUNCE_MS);
    expect(h.socket().types()).toEqual(["bind", "bind"]);
  });

  it("flags frames that stop while the tab shows, and resumes on the next press", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.socket().receive(
      JSON.stringify({ type: "bound", n: 1, catalog_digest: "d", issues: [] }),
    );
    h.socket().receive(encodeFrame(0.1, 1, new Uint8Array(3)));
    vi.advanceTimersByTime(STALL_MS);
    expect(h.store.getState().stalled).toBe(false);
    h.press();
    vi.advanceTimersByTime(STALL_MS);
    expect(h.store.getState().stalled).toBe(true);
    expect(h.socket().types()).toEqual([]);
    h.press();
    expect(h.socket().types()).toEqual(["resume"]);
    h.socket().receive(encodeFrame(0.2, 2, new Uint8Array(3)));
    expect(h.store.getState().stalled).toBe(false);
  });

  it("drops frames until bound, then those of the wrong length", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.socket().receive(hello(64));
    h.socket().receive(encodeFrame(0.1, 1, new Uint8Array(64 * 3)));
    expect(h.frames).toHaveLength(0);
    h.socket().receive(
      JSON.stringify({
        type: "bound",
        n: 128,
        catalog_digest: "d",
        issues: [],
      }),
    );
    h.socket().receive(encodeFrame(0.2, 2, new Uint8Array(64 * 3)));
    h.socket().receive(encodeFrame(0.3, 3, new Uint8Array(128 * 3)));
    expect(h.frames.map((f) => f.seq)).toEqual([3]);
    expect(h.store.getState()).toMatchObject({
      boundN: 128,
      catalogDigest: "d",
    });
  });

  it("keeps the engine's values from hello and each params echo", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.socket().receive(
      JSON.stringify({
        type: "hello",
        n: 64,
        fps: 30,
        patterns: ["a", "b"],
        pattern: "a",
        params: [
          {
            name: "speed",
            kind: "float",
            label: "Speed",
            default: 1,
            lo: 0,
            hi: 2,
            step: 0.1,
            decimals: 1,
          },
          {
            name: "color",
            kind: "color",
            label: "Color",
            default: { h: 200, s: 1, v: 1 },
            parts: {
              h: { lo: 0, hi: 360, step: 2, decimals: 0 },
              s: { lo: 0, hi: 1, step: 0.005, decimals: 3 },
              v: { lo: 0, hi: 1, step: 0.005, decimals: 3 },
            },
          },
        ],
        values: { speed: 1.5 },
      }),
    );
    // A value the hello leaves out starts at its default.
    expect(h.store.getState().accepted).toEqual({
      speed: 1.5,
      color: { h: 200, s: 1, v: 1 },
    });
    h.socket().receive(
      JSON.stringify({
        type: "params",
        values: { speed: 0.4, color: { h: 30, s: 1, v: 0.5 } },
      }),
    );
    expect(h.store.getState().accepted).toEqual({
      speed: 0.4,
      color: { h: 30, s: 1, v: 0.5 },
    });
    h.socket().receive(
      JSON.stringify({
        type: "refused",
        control: "set",
        name: "speed",
        reason: "speed must be within 0–2",
      }),
    );
    expect(h.store.getState().refusal?.reason).toBe("speed must be within 0–2");
    expect(h.store.getState().refusedAt.speed).toBeGreaterThan(0);
    h.socket().receive(
      JSON.stringify({ type: "refused", control: "pattern", reason: "no" }),
    );
    expect(Object.keys(h.store.getState().refusedAt)).toEqual(["speed"]);
    h.socket().receive(
      JSON.stringify({ type: "power", watts: 42, uncapped_watts: 84 }),
    );
    h.socket().receive(
      JSON.stringify({
        type: "status",
        error: "ZeroDivisionError",
        source: "render",
        pattern: "a",
      }),
    );
    expect(h.store.getState()).toMatchObject({
      watts: 42,
      uncappedWatts: 84,
      engineError: "ZeroDivisionError",
    });
  });

  it("pauses while the tab is hidden and resumes when it shows", () => {
    const h = harness(true);
    h.client.start();
    h.socket().open();
    expect(h.socket().types()).toEqual(["pause"]);
    h.setHidden(false);
    h.setHidden(true);
    expect(h.socket().types()).toEqual(["pause", "resume", "pause"]);
  });

  it("reconnects with backoff and binds again, keeping the chosen pattern", () => {
    const h = harness();
    h.client.bind(DEFAULT_ARRANGEMENT);
    h.client.start();
    const first = h.socket();
    first.open();
    h.client.setPattern("plasma");
    first.receive(
      JSON.stringify({ type: "bound", n: 64, catalog_digest: "d", issues: [] }),
    );
    first.receive(
      JSON.stringify({ type: "power", watts: 1, uncapped_watts: 2 }),
    );
    first.close();
    expect(h.store.getState()).toMatchObject({
      connection: "closed",
      boundN: null,
      watts: null,
      uncappedWatts: null,
    });
    vi.advanceTimersByTime(999);
    expect(FakeSocket.all).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.all).toHaveLength(2);
    // A socket that never opens doubles the wait.
    h.socket().close();
    vi.advanceTimersByTime(1999);
    expect(FakeSocket.all).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.all).toHaveLength(3);
    h.socket().open();
    expect(h.socket().types()).toEqual(["bind", "pattern"]);
  });

  it("backs off when sessions open but never bind", () => {
    const h = harness();
    h.client.bind(DEFAULT_ARRANGEMENT);
    h.client.start();
    for (const wait of [1000, 2000, 4000, 8000, 10_000, 10_000]) {
      h.socket().open();
      h.socket().close();
      const count = FakeSocket.all.length;
      vi.advanceTimersByTime(wait - 1);
      expect(FakeSocket.all).toHaveLength(count);
      vi.advanceTimersByTime(1);
      expect(FakeSocket.all).toHaveLength(count + 1);
    }
  });

  it("stops for good on stop()", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.client.stop();
    vi.advanceTimersByTime(60_000);
    expect(FakeSocket.all).toHaveLength(1);
  });
});

import type { Frame } from "../../../src/wire/protocol";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_ARRANGEMENT } from "../../../src/studio/store/doc";
import { initialSession, type SessionState } from "../../../src/studio/store/session";
import { BIND_DEBOUNCE_MS, SessionClient, STALL_MS } from "../../../src/studio/session/client";
import { encodeFrame } from "../../../src/studio/session/protocol";
import { FakeWebSocket } from "../../fixtures/fakeWebSocket";

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
  const held: (() => void)[] = [];
  const activity = new EventTarget();
  const client = new SessionClient({
    url: "ws://test/ws/session",
    WebSocket: FakeWebSocket as unknown as typeof WebSocket,
    store,
    visibility,
    activity,
    onFrame: (f) => frames.push(f),
    requestFrame: (cb) => held.push(cb),
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
    flush: () => {
      for (const cb of held.splice(0)) cb();
    },
    press: () => activity.dispatchEvent(new Event("pointerdown")),
    socket: () => FakeWebSocket.made.at(-1)!,
  };
}

/** The engine's hello, sent on connect: the placeholder rig. */
const hello = (n: number) => ({
  type: "hello",
  ...shape(n),
  display_gamma: 2.2,
  build: null,
  capabilities: ["ack", "look"],
});

/** The layout after a bind: the bound rig. */
const bound = (n: number) => ({ type: "layout", ...shape(n) });

function shape(n: number) {
  return {
    n,
    total: n,
    positions: Array.from({ length: n }, (_, i) => [i / n, 0, 0]),
    is3d: false,
    room: null,
  };
}

describe("SessionClient", () => {
  beforeEach(() => {
    FakeWebSocket.made = [];
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  it("binds as soon as the socket opens", () => {
    const h = harness();
    h.client.bind(DEFAULT_ARRANGEMENT);
    h.client.start();
    h.socket().open();
    expect(h.socket().types()).toEqual(["bind"]);
    expect(h.socket().sent[0]!.arrangement).toEqual(
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
    expect(h.socket().sent.map((s) => s.arrangement.name)).toEqual([
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
    h.socket().receive(hello(256));
    h.socket().receive(bound(1));
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
    h.socket().receive(bound(128));
    h.socket().receive(encodeFrame(0.2, 2, new Uint8Array(64 * 3)));
    h.socket().receive(encodeFrame(0.3, 3, new Uint8Array(128 * 3)));
    expect(h.frames.map((f) => f.seq)).toEqual([3]);
    expect(h.store.getState().boundN).toBe(128);
  });

  it("opens the wire on the engine's hello, which a layout leaves open", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    expect(h.client.wire.getState().connected).toBe(false);
    h.socket().receive(hello(256));
    expect(h.client.wire.getState()).toMatchObject({
      connected: true,
      gamma: 2.2,
      session: 1,
    });
    expect(h.store.getState().boundN).toBeNull();
    h.socket().receive({
      type: "declare",
      params: [
        {
          name: "layers.base.waves.freq",
          kind: "float",
          label: "Freq",
          default: 3,
          lo: 0,
          hi: 10,
          step: 0.1,
          decimals: 1,
          layer: "base",
          node: "waves",
        },
      ],
    });
    h.socket().receive({
      type: "params",
      values: { "layers.base.waves.freq": 4 },
    });
    // The layout after a bind leaves every state as it is.
    h.socket().receive(bound(64));
    const wire = h.client.wire;
    expect(wire.getState().session).toBe(1);
    const [freq] = wire.getState().params;
    expect(freq && wire.value(freq)).toBe(4);
    h.socket().receive({ type: "power", watts: 42, uncapped_watts: 84 });
    h.socket().receive({
      type: "status",
      error: "ZeroDivisionError",
      source: "render",
      path: "layers.base",
    });
    expect(h.store.getState()).toMatchObject({ watts: 42, uncappedWatts: 84 });
    expect(wire.getState().error?.text).toBe("ZeroDivisionError");
  });

  it("sends the editor's requests on the same socket, a drag's on the next frame", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.client.socket.sendLatest({
      type: "set",
      name: "layers.base.waves.freq",
      value: 4,
    });
    h.client.socket.send({ type: "surprise", seed: null });
    h.client.socket.sendLatest({
      type: "set",
      name: "layers.base.waves.freq",
      value: 5,
    });
    h.flush();
    expect(h.socket().sent).toEqual([
      { type: "set", name: "layers.base.waves.freq", value: 4 },
      { type: "surprise", seed: null },
      { type: "set", name: "layers.base.waves.freq", value: 5 },
    ]);
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

  it("reconnects with backoff and binds again", () => {
    const h = harness();
    h.client.bind(DEFAULT_ARRANGEMENT);
    h.client.start();
    const first = h.socket();
    first.open();
    first.receive(hello(256));
    first.receive(bound(64));
    first.receive({ type: "power", watts: 1, uncapped_watts: 2 });
    first.close();
    expect(h.client.wire.getState().connected).toBe(false);
    expect(h.store.getState()).toMatchObject({
      boundN: null,
      watts: null,
      uncappedWatts: null,
    });
    vi.advanceTimersByTime(999);
    expect(FakeWebSocket.made).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.made).toHaveLength(2);
    // A socket that never opens doubles the wait.
    h.socket().close();
    vi.advanceTimersByTime(1999);
    expect(FakeWebSocket.made).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.made).toHaveLength(3);
    h.socket().open();
    expect(h.socket().types()).toEqual(["bind"]);
  });

  it("backs off when sessions open but never bind", () => {
    const h = harness();
    h.client.bind(DEFAULT_ARRANGEMENT);
    h.client.start();
    for (const wait of [1000, 2000, 4000, 8000, 10_000, 10_000]) {
      h.socket().open();
      h.socket().close();
      const count = FakeWebSocket.made.length;
      vi.advanceTimersByTime(wait - 1);
      expect(FakeWebSocket.made).toHaveLength(count);
      vi.advanceTimersByTime(1);
      expect(FakeWebSocket.made).toHaveLength(count + 1);
    }
  });

  it("stops for good on stop()", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.client.stop();
    vi.advanceTimersByTime(60_000);
    expect(FakeWebSocket.made).toHaveLength(1);
  });
});

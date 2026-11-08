import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { frameGap, STALE_MS } from "../../../src/health/health";
import { DEFAULT_ARRANGEMENT } from "../../../src/studio/store/share";
import { BIND_DEBOUNCE_MS, SessionClient } from "../../../src/studio/session/client";
import { encodeFrame } from "../../../src/wire/protocol";
import { FakeWebSocket } from "../../fixtures/fakeWebSocket";
import { first, SESSION_GREETING, SESSION_LAYOUT, SESSION_POWER } from "../../fixtures/messages";

function harness(hidden = false) {
  const listeners = new Set<() => void>();
  const visibility = {
    hidden,
    addEventListener: (_: string, fn: () => void) => listeners.add(fn),
    removeEventListener: (_: string, fn: () => void) => listeners.delete(fn),
  } as unknown as Document;
  const held: (() => void)[] = [];
  const activity = new EventTarget();
  const client = new SessionClient({
    url: "ws://test/ws/session",
    WebSocket: FakeWebSocket as unknown as typeof WebSocket,
    visibility,
    activity,
    requestFrame: (cb) => held.push(cb),
  });
  const setHidden = (h: boolean) => {
    (visibility as { hidden: boolean }).hidden = h;
    for (const fn of listeners) fn();
  };
  return {
    client,
    wire: client.wire,
    setHidden,
    flush: () => {
      for (const cb of held.splice(0)) cb();
    },
    press: () => activity.dispatchEvent(new Event("pointerdown")),
    socket: () => FakeWebSocket.made.at(-1)!,
    /** The engine's greeting on the placeholder rig, as a new session sends it. */
    greet: () => {
      for (const msg of SESSION_GREETING) FakeWebSocket.made.at(-1)!.receive(msg);
    },
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

  it("resumes on the first press after frames stop, once a spell", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    h.greet();
    h.socket().receive(SESSION_LAYOUT);
    // The fake clock starts at 0, which the store reads as no frame yet.
    vi.advanceTimersByTime(10);
    h.socket().receive(encodeFrame(0.1, 1, new Uint8Array(SESSION_LAYOUT.n * 3)));
    vi.advanceTimersByTime(STALE_MS - 1);
    h.press();
    expect(h.socket().types()).toEqual([]);
    vi.advanceTimersByTime(2);
    expect(frameGap(performance.now(), h.wire.lastFrameAt)).toBeGreaterThan(0);
    h.press();
    h.press();
    expect(h.socket().types()).toEqual(["resume"]);
    h.socket().receive(encodeFrame(0.2, 2, new Uint8Array(SESSION_LAYOUT.n * 3)));
    expect(frameGap(performance.now(), h.wire.lastFrameAt)).toBe(0);
  });

  it("resumes once after a layout that no frame follows, as after a reconnect or a pause while hidden", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    vi.advanceTimersByTime(10);
    h.greet();
    h.socket().receive(SESSION_LAYOUT);
    vi.advanceTimersByTime(STALE_MS - 1);
    h.press();
    expect(h.socket().types()).toEqual([]);
    vi.advanceTimersByTime(2);
    h.press();
    h.press();
    expect(h.socket().types()).toEqual(["resume"]);
    // A reconnect starts the spell over from its own hello.
    h.socket().close();
    vi.advanceTimersByTime(1000);
    h.socket().open();
    h.greet();
    h.socket().receive(SESSION_LAYOUT);
    vi.advanceTimersByTime(STALE_MS + 1);
    h.press();
    expect(h.socket().types()).toEqual(["resume"]);
  });

  it("opens the wire on the engine's hello, which a layout leaves open", () => {
    const h = harness();
    h.client.start();
    h.socket().open();
    expect(h.wire.getState().connected).toBe(false);
    h.greet();
    const hello = first("hello", SESSION_GREETING);
    expect(h.wire.getState()).toMatchObject({ connected: true, gamma: hello.display_gamma, session: 1 });
    expect(h.wire.getState().map?.n).toBe(hello.n);
    const [knob] = h.wire.getState().params;
    const value = knob && h.wire.value(knob);
    expect(value).not.toBeUndefined();
    // The layout after a bind replaces the map and leaves every state as it is.
    h.socket().receive(SESSION_LAYOUT);
    expect(h.wire.getState().session).toBe(1);
    expect(h.wire.getState().map?.n).toBe(SESSION_LAYOUT.n);
    expect(knob && h.wire.value(knob)).toBe(value);
    h.socket().receive(SESSION_POWER);
    expect(h.wire.getState().power).toEqual({ watts: SESSION_POWER.watts, uncapped_watts: SESSION_POWER.uncapped_watts });
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
    h.greet();
    first.receive(SESSION_LAYOUT);
    first.receive(SESSION_POWER);
    first.close();
    expect(h.wire.getState()).toMatchObject({ connected: false, power: null });
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

  it("starts the backoff over once a bind works", () => {
    const h = harness();
    h.client.start();
    for (const wait of [1000, 2000]) {
      h.socket().close();
      vi.advanceTimersByTime(wait);
    }
    h.socket().open();
    h.greet();
    h.socket().receive(SESSION_LAYOUT);
    h.socket().close();
    const count = FakeWebSocket.made.length;
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.made).toHaveLength(count + 1);
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

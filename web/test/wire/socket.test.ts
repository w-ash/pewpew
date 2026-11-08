import { afterEach, expect, test, vi } from "vitest";
import { decodeParam } from "../../src/params/kinds";
import { setParam } from "../../src/wire/protocol";
import { RECONNECT_MAX_MS, RECONNECT_MS, Socket, socketUrl } from "../../src/wire/socket";
import { WireStore } from "../../src/wire/store";
import { record } from "../fixtures/describe";
import { FakeWebSocket } from "../fixtures/fakeWebSocket";
import { hello, SESSION_GREETING, SESSION_POWER, SESSION_REFUSED } from "../fixtures/messages";

function setup(build: string | null = null, reload = () => {}) {
  FakeWebSocket.made = [];
  const frames: (() => void)[] = [];
  const store = new WireStore();
  const socket = new Socket(store, {
    url: "ws://test/ws",
    WebSocket: FakeWebSocket as unknown as typeof WebSocket,
    requestFrame: (cb) => frames.push(cb),
    now: () => 500,
    build,
    reload,
  });
  socket.start();
  const ws = FakeWebSocket.made[0]!;
  ws.open();
  const flush = () => frames.splice(0).forEach((f) => f());
  return { store, socket, ws, flush };
}

afterEach(() => vi.useRealTimers());

test("connects to /ws for array-buffer frames", () => {
  const { ws } = setup();
  expect(ws.url).toBe("ws://test/ws");
  expect(ws.binaryType).toBe("arraybuffer");
});

test("text goes to the store, frames carry engine time and bytes", () => {
  const { store, ws } = setup();
  ws.onmessage!({ data: JSON.stringify(hello()) });
  expect(store.getState().connected).toBe(true);
  const buf = new ArrayBuffer(8 + 6);
  const view = new DataView(buf);
  view.setFloat32(0, 1.5, true);
  view.setUint32(4, 7, true);
  new Uint8Array(buf, 8).set([1, 2, 3, 4, 5, 6]);
  ws.onmessage!({ data: buf });
  expect(store.getFrame()).toMatchObject({ t: 1.5, seq: 7 });
  expect(Array.from(store.getFrame()!.rgb)).toEqual([1, 2, 3, 4, 5, 6]);
  expect(store.lastFrameAt).toBe(500);
});

test("sets coalesce per animation frame, the newest winning per param", () => {
  const { socket, ws, flush } = setup();
  const level = decodeParam(record("zoo_test", "level"));
  const color = decodeParam(record("zoo_test", "color"));
  setParam(socket, level, 0.1);
  setParam(socket, level, 0.2);
  setParam(socket, color, { h: 1, s: 1, v: 1 });
  expect(ws.sent).toEqual([]);
  flush();
  expect(ws.sent).toEqual([
    { type: "set", name: "level", value: 0.2 },
    { type: "set", name: "color", value: { h: 1, s: 1, v: 1 } },
  ]);
  setParam(socket, level, 0.3);
  flush();
  expect(ws.sent).toHaveLength(3);
});

test("a message sent at once goes after the held sets; masters coalesce like sets", () => {
  const { socket, ws, flush } = setup();
  const level = decodeParam(record("zoo_test", "level"));
  setParam(socket, level, 0.4);
  socket.sendLatest({ type: "master", value: 0.2 });
  socket.sendLatest({ type: "master", value: 0.3 });
  socket.send({ type: "save", name: "x", fade: null, master: true });
  expect(ws.sent).toEqual([
    { type: "set", name: "level", value: 0.4 },
    { type: "master", value: 0.3 },
    { type: "save", name: "x", fade: null, master: true },
  ]);
  flush();
  expect(ws.sent).toHaveLength(3);
});

test("a closed socket reconnects after a second", () => {
  vi.useFakeTimers();
  const { store, ws } = setup();
  ws.onmessage!({ data: JSON.stringify(hello()) });
  ws.close();
  expect(store.getState().connected).toBe(false);
  expect(FakeWebSocket.made).toHaveLength(1);
  vi.advanceTimersByTime(RECONNECT_MS);
  expect(FakeWebSocket.made).toHaveLength(2);
});

test("an engine that serves another page build reloads the tab instead of greeting it", () => {
  const reload = vi.fn();
  const { store, ws } = setup("aaaa", reload);
  ws.onmessage!({ data: JSON.stringify(hello({ build: "bbbb" })) });
  expect(reload).toHaveBeenCalledOnce();
  expect(store.getState().connected).toBe(false);
  ws.onmessage!({ data: JSON.stringify(hello({ build: "aaaa" })) });
  ws.onmessage!({ data: JSON.stringify(hello({ build: null })) });
  expect(reload).toHaveBeenCalledOnce();
  expect(store.getState().session).toBe(2);
});

test("nothing is sent while the socket is not open", () => {
  const { socket, ws } = setup();
  ws.readyState = 0;
  socket.send({ type: "scan" });
  expect(ws.sent).toEqual([]);
});

test("an ask goes with an id and settles on the engine's answer to that id, taken on an ack, or untaken when the socket closes", async () => {
  const { socket, store, ws, flush } = setup();
  ws.onmessage!({ data: JSON.stringify(hello()) });
  const level = decodeParam(record("zoo_test", "level"));
  setParam(socket, level, 0.5);
  const settled: string[] = [];
  void socket.ask({ type: "surprise", seed: null }).then((took) => settled.push(`surprise ${took}`));
  void socket.ask({ type: "keep" }).then((took) => settled.push(`keep ${took}`));
  flush();
  expect(ws.sent).toEqual([
    { type: "set", name: "level", value: 0.5 },
    { type: "surprise", seed: null, id: 1 },
    { type: "keep", id: 2 },
  ]);
  ws.onmessage!({ data: JSON.stringify({ type: "ack", id: 9, control: "surprise" }) });
  ws.onmessage!({ data: JSON.stringify({ type: "refused", control: "keep", name: null, id: 2, reason: "no looks file" }) });
  await Promise.resolve();
  expect(settled).toEqual(["keep false"]);
  expect(store.getState().refusals.keep?.reason).toBe("no looks file"); // a refusal still reaches the store
  ws.onmessage!({ data: JSON.stringify({ type: "ack", id: 1, control: "surprise" }) });
  await Promise.resolve();
  expect(settled).toEqual(["keep false", "surprise true"]);
  void socket.ask({ type: "vary", strength: null, seed: null }).then((took) => settled.push(`vary ${took}`));
  ws.close();
  await Promise.resolve();
  expect(settled.at(-1)).toBe("vary false");
});

test("an ask the socket cannot send settles at once, not taken", async () => {
  const { socket, ws } = setup();
  ws.readyState = 0;
  expect(await socket.ask({ type: "surprise", seed: null })).toBe(false);
  expect(ws.sent).toEqual([]);
});

test("a Gallery session's messages reach the store as any do", () => {
  const { store, ws } = setup();
  for (const msg of SESSION_GREETING) ws.receive(msg);
  ws.receive(SESSION_POWER);
  ws.receive(SESSION_REFUSED.message);
  expect(store.getState()).toMatchObject({
    connected: true,
    session: 1,
    power: { watts: SESSION_POWER.watts, uncapped_watts: SESSION_POWER.uncapped_watts },
    refusals: { message: { reason: SESSION_REFUSED.message.reason } },
  });
  expect(store.getState().capabilities).toContain("gallery");
  ws.close();
  expect(store.getState().power).toBeNull();
});

test("an exported answers an export's ask, taken, and the store keeps it before the ask settles", async () => {
  const { socket, store, ws } = setup();
  ws.receive(hello());
  const file = { version: 4, current: "warm", looks: {}, cycle: [] };
  const asked = socket.ask({ type: "export", looks: null, share: false }).then((took) => [took, store.exported?.file]);
  expect(ws.sent).toEqual([{ type: "export", looks: null, share: false, id: 1 }]);
  ws.receive({ type: "exported", id: 1, file, gallery: null });
  expect(await asked).toEqual([true, file]);
});

/** Close the newest socket, after a hello when `greeted`; how long until the next one opens, in ms. */
function waitAfterClose(greeted: boolean): number {
  const ws = FakeWebSocket.made.at(-1)!;
  if (greeted) ws.onmessage!({ data: JSON.stringify(hello()) });
  ws.close();
  const made = FakeWebSocket.made.length;
  let waited = 0;
  while (FakeWebSocket.made.length === made && waited < 60_000) {
    vi.advanceTimersByTime(1);
    waited++;
  }
  return waited;
}

test("refused before a hello, the socket waits twice as long each time, to the most; a hello starts again", () => {
  vi.useFakeTimers();
  vi.spyOn(Math, "random").mockReturnValue(0);
  setup();
  expect([1, 2, 3, 4, 5].map(() => waitAfterClose(false))).toEqual([RECONNECT_MS, 2000, 4000, 8000, RECONNECT_MAX_MS]);
  expect(waitAfterClose(false)).toBe(RECONNECT_MAX_MS);
  expect(waitAfterClose(true)).toBe(RECONNECT_MS);
  expect(waitAfterClose(false)).toBe(2 * RECONNECT_MS);
  vi.restoreAllMocks();
});

test("each wait is less up to half at random", () => {
  vi.useFakeTimers();
  vi.spyOn(Math, "random").mockReturnValue(0.5);
  setup();
  expect(waitAfterClose(true)).toBe(0.75 * RECONNECT_MS);
  expect(waitAfterClose(false)).toBe(1.5 * RECONNECT_MS);
  vi.restoreAllMocks();
});

test("the socket's URL follows the page: its scheme, host and query, and a share's id from its path", () => {
  const page = (href: string) => {
    const { protocol, host, pathname, search } = new URL(href);
    return socketUrl({ protocol, host, pathname, search });
  };
  const id = "AbCdEfGhIjKlMnOpQr_-12";
  expect(page("http://127.0.0.1:7447/")).toBe("ws://127.0.0.1:7447/ws");
  expect(page("https://gallery.example/")).toBe("wss://gallery.example/ws");
  expect(page(`https://gallery.example/a/${id}`)).toBe(`wss://gallery.example/ws?a=${id}`);
  expect(page(`http://localhost:8000/a/${id}?x=1`)).toBe(`ws://localhost:8000/ws?x=1&a=${id}`);
  expect(page("http://127.0.0.1:7447/?debug")).toBe("ws://127.0.0.1:7447/ws?debug");
  // Not a share's path: no id.
  expect(page("https://gallery.example/a/short")).toBe("wss://gallery.example/ws");
});

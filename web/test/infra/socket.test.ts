import { afterEach, expect, test, vi } from "vitest";
import { decodeParam } from "../../src/params/kinds";
import { setParam } from "../../src/wire/protocol";
import { RECONNECT_MS, Socket } from "../../src/wire/socket";
import { WireStore } from "../../src/wire/store";
import { record } from "../fixtures/describe";
import { hello } from "../fixtures/messages";

class FakeWebSocket {
  static readonly OPEN = 1;
  static made: FakeWebSocket[] = [];
  readyState = 1;
  binaryType = "blob";
  sent: unknown[] = [];
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(readonly url: string) {
    FakeWebSocket.made.push(this);
  }
  send(text: string) {
    this.sent.push(JSON.parse(text));
  }
  close() {
    this.onclose?.();
  }
}

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
  const level = decodeParam(record("zoo", "level"));
  const color = decodeParam(record("zoo", "color"));
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
  const level = decodeParam(record("zoo", "level"));
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

test("an ask goes with an id and settles on the engine's answer to that id, or when the socket closes", async () => {
  const { socket, store, ws, flush } = setup();
  ws.onmessage!({ data: JSON.stringify(hello()) });
  const level = decodeParam(record("zoo", "level"));
  setParam(socket, level, 0.5);
  const settled: string[] = [];
  void socket.ask({ type: "surprise", seed: null }).then(() => settled.push("surprise"));
  void socket.ask({ type: "keep" }).then(() => settled.push("keep"));
  flush();
  expect(ws.sent).toEqual([
    { type: "set", name: "level", value: 0.5 },
    { type: "surprise", seed: null, id: 1 },
    { type: "keep", id: 2 },
  ]);
  ws.onmessage!({ data: JSON.stringify({ type: "ack", id: 9, control: "surprise" }) });
  ws.onmessage!({ data: JSON.stringify({ type: "refused", control: "keep", name: null, id: 2, reason: "no looks file" }) });
  await Promise.resolve();
  expect(settled).toEqual(["keep"]);
  expect(store.getState().refusals.keep?.reason).toBe("no looks file"); // a refusal still reaches the store
  ws.onmessage!({ data: JSON.stringify({ type: "ack", id: 1, control: "surprise" }) });
  await Promise.resolve();
  expect(settled).toEqual(["keep", "surprise"]);
  void socket.ask({ type: "vary", strength: null, seed: null }).then(() => settled.push("vary"));
  ws.close();
  await Promise.resolve();
  expect(settled.at(-1)).toBe("vary");
});

test("an ask the socket cannot send settles at once", async () => {
  const { socket, ws } = setup();
  ws.readyState = 0;
  let settled = false;
  await socket.ask({ type: "surprise", seed: null }).then(() => (settled = true));
  expect(settled).toBe(true);
  expect(ws.sent).toEqual([]);
});

test("a page's own messages: its types go to it, not the store; it sends its own; opens and closes are told", () => {
  FakeWebSocket.made = [];
  const store = new WireStore();
  const own: unknown[] = [];
  const told: string[] = [];
  const socket = new Socket<{ type: "bind"; arrangement: string }>(store, {
    url: "ws://test/ws/session",
    WebSocket: FakeWebSocket as unknown as typeof WebSocket,
    build: null,
    ownTypes: ["hello", "bound"],
    onOwnMessage: (msg) => own.push(msg),
    onOpen: () => told.push("open"),
    onClose: () => told.push("close"),
  });
  socket.start();
  const ws = FakeWebSocket.made[0]! as FakeWebSocket & { onopen: () => void };
  ws.onopen();
  ws.onmessage!({ data: JSON.stringify({ type: "hello", n: 64, fps: 30, capabilities: [] }) });
  ws.onmessage!({ data: JSON.stringify({ type: "bound", n: 64 }) });
  ws.onmessage!({ data: JSON.stringify({ type: "status", error: "x", source: "bind", path: null }) });
  expect(own).toEqual([{ type: "hello", n: 64, fps: 30, capabilities: [] }, { type: "bound", n: 64 }]);
  expect(store.getState()).toMatchObject({ connected: false, session: 0, error: { text: "x", source: "bind" } });
  socket.send({ type: "bind", arrangement: "rig" });
  expect(ws.sent).toEqual([{ type: "bind", arrangement: "rig" }]);
  ws.close();
  expect(told).toEqual(["open", "close"]);
});

test("the wait before a reconnect is the page's to give, and a stopped socket stays closed", () => {
  vi.useFakeTimers();
  FakeWebSocket.made = [];
  const socket = new Socket(new WireStore(), {
    url: "ws://test/ws",
    WebSocket: FakeWebSocket as unknown as typeof WebSocket,
    build: null,
    reconnectMs: () => 5000,
  });
  socket.start();
  FakeWebSocket.made[0]!.close();
  vi.advanceTimersByTime(4999);
  expect(FakeWebSocket.made).toHaveLength(1);
  vi.advanceTimersByTime(1);
  expect(FakeWebSocket.made).toHaveLength(2);
  socket.stop();
  vi.advanceTimersByTime(60_000);
  expect(FakeWebSocket.made).toHaveLength(2);
});

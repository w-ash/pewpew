// A Gallery session's idle pause, and its reconnects that back off.
import { act } from "react";
import { afterEach, expect, test } from "vitest";
import { backoff, RECONNECT_MAX_MS } from "../../src/share/backoff";
import { useIdlePause } from "../../src/share/useIdlePause";
import { RECONNECT_MS } from "../../src/wire/socket";
import { encodeFrame, parseFrame } from "../../src/wire/protocol";
import { WireStore } from "../../src/wire/store";
import { galleryGreeting, hello } from "../fixtures/messages";
import { renderWired } from "../harness";

let hidden = false;
Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });

afterEach(() => {
  hidden = false;
});

function Idle({ on }: { on: boolean }) {
  useIdlePause(on);
  return null;
}

const pauses = (sent: readonly { type: string }[]) => sent.filter((m) => m.type === "pause" || m.type === "resume").map((m) => m.type);

function setHidden(on: boolean) {
  hidden = on;
  document.dispatchEvent(new Event("visibilitychange"));
}

test("the tab hiding sends pause, and showing sends resume", async () => {
  const { sent } = await renderWired(<Idle on />, galleryGreeting());
  expect(pauses(sent)).toEqual([]);
  setHidden(true);
  setHidden(false);
  expect(pauses(sent)).toEqual(["pause", "resume"]);
});

test("a hello that comes to a hidden tab is answered with pause", async () => {
  const { sent, receive } = await renderWired(<Idle on />, galleryGreeting());
  hidden = true;
  receive(galleryGreeting()[0]!);
  expect(pauses(sent)).toEqual(["pause"]);
});

test("a press while frames are stale sends resume, once a stale spell; a press while they flow sends nothing", async () => {
  const { sent, store } = await renderWired(<Idle on />, galleryGreeting());
  const frame = parseFrame(encodeFrame(1, 1, new Uint8Array(12)));
  act(() => store.receiveFrame(frame, performance.now()));
  window.dispatchEvent(new PointerEvent("pointerdown"));
  expect(pauses(sent)).toEqual([]);
  act(() => store.receiveFrame(frame, performance.now() - 10_000));
  window.dispatchEvent(new PointerEvent("pointerdown"));
  window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
  window.dispatchEvent(new WheelEvent("wheel"));
  expect(pauses(sent)).toEqual(["resume"]);
});

test("off (no `pause` capability), it sends nothing", async () => {
  const { sent } = await renderWired(<Idle on={false} />, galleryGreeting());
  setHidden(true);
  setHidden(false);
  expect(pauses(sent)).toEqual([]);
});

test("the Gallery's reconnects double while none has a hello, to the most, and start again after one that has", () => {
  const store = new WireStore();
  const wait = backoff(store);
  store.receive(hello());
  store.disconnected();
  expect(wait()).toBe(RECONNECT_MS);
  expect([wait(), wait(), wait(), wait(), wait()]).toEqual([2000, 4000, 8000, RECONNECT_MAX_MS, RECONNECT_MAX_MS]);
  store.receive(hello());
  store.disconnected();
  expect(wait()).toBe(RECONNECT_MS);
  expect(wait()).toBe(2 * RECONNECT_MS);
});

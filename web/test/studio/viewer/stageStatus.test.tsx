import { act } from "react";
import { expect, test } from "vitest";
import { render } from "vitest-browser-react";
import { encodeFrame, parseFrame } from "../../../src/wire/protocol";
import { WireContext, WireStore } from "../../../src/wire/store";
import { StageStatus } from "../../../src/studio/viewer/Stage";
import { SESSION_GREETING, SESSION_LAYOUT } from "../../fixtures/messages";

const noop = () => {};

async function status(store: WireStore) {
  const sender = { send() {}, sendLatest() {}, ask: () => Promise.resolve(true) };
  const screen = await render(
    <WireContext.Provider value={{ store, sender }}>
      <StageStatus rig={null} modelError={null} onRetry={noop} missing={[]} />
    </WireContext.Provider>,
  );
  return screen.getByTestId("stage-status");
}

const greet = (store: WireStore) => act(() => SESSION_GREETING.forEach((m) => store.receive(m)));

test("connecting, before the first hello", async () => {
  await expect.element(await status(new WireStore())).toHaveTextContent("connecting…");
});

test("binding…, from the hello's placeholder rig until the first layout", async () => {
  const store = new WireStore();
  const line = await status(store);
  greet(store);
  await expect.element(line).toHaveTextContent("binding…");
  await expect.element(line).not.toHaveTextContent("live");
  act(() => store.receive(SESSION_LAYOUT));
  await expect.element(line).toHaveTextContent(`live · ${SESSION_LAYOUT.n} px`);
});

test("a refused bind leaves it binding…, and a new hello puts it back", async () => {
  const store = new WireStore();
  const line = await status(store);
  greet(store);
  act(() => store.receive({ type: "refused", control: "bind", name: null, id: null, reason: "no" }));
  await expect.element(line).toHaveTextContent("binding…");
  act(() => store.receive(SESSION_LAYOUT));
  await expect.poll(() => line.element().textContent).toMatch(/^live · /);
  greet(store);
  await expect.element(line).toHaveTextContent("binding…");
});

test("live shows the newest frame's time", async () => {
  const store = new WireStore();
  const line = await status(store);
  greet(store);
  act(() => store.receive(SESSION_LAYOUT));
  act(() => store.receiveFrame(parseFrame(encodeFrame(1.5, 1, new Uint8Array(SESSION_LAYOUT.n * 3))), performance.now()));
  await expect.poll(() => line.element().textContent).toContain("t=1.5 s");
});

test("paused while idle, once no frame has come for a while after the layout", async () => {
  const store = new WireStore();
  const line = await status(store);
  greet(store);
  act(() => store.receive(SESSION_LAYOUT));
  store.layoutAt = 1; // long ago
  // The page looks every second.
  await act(() => new Promise((resolve) => setTimeout(resolve, 1100)));
  await expect.element(line).toHaveTextContent("paused while idle · tap to resume");
});

test("disconnected, retrying…, after a hello", async () => {
  const store = new WireStore();
  const line = await status(store);
  greet(store);
  act(() => store.receive(SESSION_LAYOUT));
  act(() => store.disconnected());
  await expect.element(line).toHaveTextContent("disconnected, retrying…");
});

import type { ReactNode } from "react";
import { act } from "react";
import { render } from "vitest-browser-react";
import type { ClientMessage, Sender, ServerMessage } from "../../src/infra/wire/protocol";
import { WireContext, WireStore } from "../../src/infra/wire/store";
import { ArmClockContext, CONFIRM_MIN_MS, type ArmClock } from "../../src/ui/common/useArm";
import { LayoutProvider } from "../../src/ui/layout/LayoutMode";
import { LayerList } from "../../src/ui/stack/LayerList";
import { useLayerSelection } from "../../src/ui/stack/selection";
import "../../src/ui/styles.css";
import { greeting } from "../fixtures/messages";

// The clock two-press buttons read. It moves only in pastDoubleTap, and no arm
// lapses on it. Vitest's fake timers cannot do this job: in browser mode they
// tick in real time while a click is pending, so a slow click would pass the
// double-tap guard.
let now = 0;
const clock: ArmClock = { now: () => now, after: () => () => {} };

/** A page wired to a store and a sender that records what it sends. What it `ask`s waits until `answer`
 * settles it, as the engine's ack or refusal would. */
export async function renderWired(ui: ReactNode, pattern = "zoo") {
  const store = new WireStore();
  for (const msg of greeting(pattern)) store.receive(msg);
  const sent: ClientMessage[] = [];
  const asked: (() => void)[] = [];
  const sender: Sender = {
    send: (msg) => sent.push(msg),
    sendLatest: (msg) => sent.push(msg),
    ask: (msg) => {
      sent.push(msg);
      return new Promise((resolve) => asked.push(resolve));
    },
  };
  const screen = await render(
    <WireContext.Provider value={{ store, sender }}>
      <ArmClockContext.Provider value={clock}>
        <LayoutProvider>{ui}</LayoutProvider>
      </ArmClockContext.Provider>
    </WireContext.Provider>,
  );
  // The inlined fonts, so a width measured now is the width the page keeps.
  await document.fonts.ready;
  const receive = (msg: ServerMessage) => act(() => store.receive(msg));
  /** Settle the oldest request still asked. */
  const answer = () => act(async () => asked.shift()?.());
  return { screen, store, sent, receive, answer };
}

/** Wait out the double-tap guard, so the next press of an armed button fires. */
export function pastDoubleTap(): void {
  now += CONFIRM_MIN_MS;
}

/** The running look's layers, as the slot shows them, with a selection of their own. */
export function Layers() {
  const selection = useLayerSelection();
  return <LayerList selection={selection} onAdd={() => {}} />;
}

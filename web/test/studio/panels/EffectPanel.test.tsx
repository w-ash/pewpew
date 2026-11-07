import { QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { expect, test } from "vitest";
import { render } from "vitest-browser-react";
import { createQueryClient } from "../../../src/studio/api/queries";
import { MockAura } from "../../../src/studio/mocks/aura";
import { MOCK_LOOKS } from "../../../src/studio/mocks/looks";
import { EffectPanel } from "../../../src/studio/panels/EffectPanel";
import type { ClientMessage, Sender, ServerMessage } from "../../../src/wire/protocol";
import { WireContext, WireStore } from "../../../src/wire/store";
import { mockApi } from "../mockApi";

/** The panel on a wire that holds the mock's `tide` and records what it sends; an `ask` settles at once. */
async function renderPanel() {
  mockApi();
  const store = new WireStore();
  store.opened({ gamma: 2.2, map: null });
  const aura = new MockAura(MOCK_LOOKS.tide!);
  for (const msg of aura.states()) store.receive(msg as unknown as ServerMessage);
  const sent: ClientMessage[] = [];
  const sender: Sender = {
    send: (msg) => sent.push(msg),
    sendLatest: (msg) => sent.push(msg),
    ask: async (msg) => {
      sent.push(msg);
    },
  };
  const screen = await render(
    <QueryClientProvider client={createQueryClient()}>
      <WireContext.Provider value={{ store, sender }}>
        <EffectPanel />
      </WireContext.Provider>
    </QueryClientProvider>,
  );
  return { screen, sent, store, aura };
}

test("the example looks show as the deck shows saved looks, and one plays whole, over its own fade", async () => {
  const { screen, sent } = await renderPanel();
  const looks = screen.getByRole("toolbar", { name: "looks" });
  // The first nine, then the rest in the list of every look.
  await expect.poll(() => looks.getByRole("button").elements()).toHaveLength(9);
  await looks.getByRole("button", { name: "copper-tide" }).click();
  expect(sent).toEqual([{ type: "look", look: MOCK_LOOKS["copper-tide"], fade: null }]);
  await expect.element(looks.getByRole("button", { name: "copper-tide" })).toHaveAttribute("aria-pressed", "true");
});

test("tide is marked at the start, in the list of every look, until a surprise plays", async () => {
  const { screen, sent } = await renderPanel();
  await screen.getByRole("button", { name: /^all \d+ looks$/ }).click();
  const all = screen.getByRole("region", { name: "looks" });
  const tide = all.getByRole("button", { name: "tide", exact: true });
  await expect.element(tide).toHaveAttribute("aria-pressed", "true");
  await all.getByRole("button", { name: "warp-lane" }).click();
  expect(sent.at(-1)).toEqual({ type: "look", look: MOCK_LOOKS["warp-lane"], fade: null });
  await expect.element(all.getByRole("button", { name: "warp-lane" })).toHaveAttribute("aria-pressed", "true");
  await expect.element(tide).toHaveAttribute("aria-pressed", "false");
  await all.getByRole("button", { name: /close/ }).click();
  await screen.getByRole("button", { name: /surprise me/ }).click();
  await screen.getByRole("button", { name: /^all \d+ looks$/ }).click();
  const again = screen.getByRole("region", { name: "looks" });
  expect(again.getByRole("button", { pressed: true }).elements()).toEqual([]);
});

test("the running look's main knobs and layers show, and a knob is set by its address", async () => {
  const { screen, sent } = await renderPanel();
  // tide's front: its waves' frequency first.
  await expect.element(screen.getByRole("spinbutton", { name: /freq/i }).first()).toBeInTheDocument();
  await expect.element(screen.getByRole("heading", { name: /^layers/ })).toBeVisible();
  for (const id of ["base", "echo", "sparks"]) await expect.element(screen.getByText(id, { exact: true }).first()).toBeInTheDocument();
  await screen.getByRole("button", { name: /increase freq/i }).first().click();
  expect(sent.at(-1)).toMatchObject({ type: "set", name: "layers.base.waves.freq" });
});

test("a surprise and a variation of what plays are asked for", async () => {
  const { screen, sent } = await renderPanel();
  await screen.getByRole("button", { name: /surprise me/ }).click();
  await screen.getByRole("button", { name: /vary this/ }).click();
  expect(sent).toEqual([
    { type: "surprise", seed: null },
    { type: "vary", strength: null, seed: null },
  ]);
});

test("a layer is added from the catalog's cards, above the one picked", async () => {
  const { screen, sent, store, aura } = await renderPanel();
  await screen.getByRole("button", { name: "+ layer" }).click();
  const cards = screen.getByRole("region", { name: "add layer" });
  // Each shelf of cards starts folded but the first.
  for (const shelf of cards.getByRole("button", { expanded: false }).all()) await shelf.click();
  await cards.getByRole("button", { name: /kaleidoscope/i }).click();
  const add = sent.at(-1);
  expect(add).toMatchObject({ type: "add_layer", below: null });
  // The engine runs it: the cards close on the new layer.
  act(() => {
    aura.add((add as { layer: Record<string, unknown> }).layer, null);
    for (const msg of aura.states()) store.receive(msg as unknown as ServerMessage);
  });
  await expect.element(screen.getByRole("button", { name: /kaleidoscope/i })).not.toBeInTheDocument();
});

import { QueryClientProvider } from "@tanstack/react-query";
import { expect, test } from "vitest";
import { createQueryClient } from "../../../src/studio/api/queries";
import { EffectPanel } from "../../../src/studio/panels/EffectPanel";
import { AURA } from "../../fixtures/messages";
import { renderWired } from "../../harness";
import { EXAMPLE_LOOKS, stubApi } from "../fixtures/api";

/** The panel on a wire that holds the engine's greeting (a look of one layer) and records what it sends. */
async function renderPanel() {
  stubApi();
  return renderWired(
    <QueryClientProvider client={createQueryClient()}>
      <EffectPanel />
    </QueryClientProvider>,
  );
}

test("the example looks show as the deck shows saved looks, and one plays whole, over its own fade", async () => {
  const { screen, sent, answer } = await renderPanel();
  const looks = screen.getByRole("toolbar", { name: "looks" });
  // The first nine, then the rest in the list of every look.
  await expect.poll(() => looks.getByRole("button").elements()).toHaveLength(9);
  await looks.getByRole("button", { name: "copper-tide" }).click();
  expect(sent).toEqual([{ type: "look", look: EXAMPLE_LOOKS["copper-tide"], fade: null }]);
  await answer();
  await expect.element(looks.getByRole("button", { name: "copper-tide" })).toHaveAttribute("aria-pressed", "true");
});

test("tide is marked at the start, in the list of every look, until a surprise plays", async () => {
  const { screen, sent, answer } = await renderPanel();
  await screen.getByRole("button", { name: /^all \d+ looks$/ }).click();
  const all = screen.getByRole("region", { name: "looks" });
  const tide = all.getByRole("button", { name: "tide", exact: true });
  await expect.element(tide).toHaveAttribute("aria-pressed", "true");
  await all.getByRole("button", { name: "warp-lane" }).click();
  expect(sent.at(-1)).toEqual({ type: "look", look: EXAMPLE_LOOKS["warp-lane"], fade: null });
  await answer();
  await expect.element(all.getByRole("button", { name: "warp-lane" })).toHaveAttribute("aria-pressed", "true");
  await expect.element(tide).toHaveAttribute("aria-pressed", "false");
  await all.getByRole("button", { name: /close/ }).click();
  await screen.getByRole("button", { name: /surprise me/ }).click();
  await answer();
  await screen.getByRole("button", { name: /^all \d+ looks$/ }).click();
  const again = screen.getByRole("region", { name: "looks" });
  expect(again.getByRole("button", { pressed: true }).elements()).toEqual([]);
});

test("the running look's main knobs and layers show, and a knob is set by its address", async () => {
  const { screen, sent } = await renderPanel();
  await expect.element(screen.getByRole("region", { name: /^base/ })).toBeVisible();
  await screen.getByRole("button", { name: /increase level/i }).first().click();
  expect(sent.at(-1)).toMatchObject({ type: "set", name: expect.any(String) });
});

test("a surprise and a variation of what plays are asked for", async () => {
  const { screen, sent, answer } = await renderPanel();
  await screen.getByRole("button", { name: /surprise me/ }).click();
  await answer();
  await screen.getByRole("button", { name: /vary this/ }).click();
  expect(sent).toEqual([
    { type: "surprise", seed: null },
    { type: "vary", strength: null, seed: null },
  ]);
});

test("a layer is added from the catalog's cards, above the one picked", async () => {
  const { screen, sent, receive } = await renderPanel();
  await screen.getByRole("button", { name: "+ layer" }).click();
  const cards = screen.getByRole("region", { name: "add layer" });
  await cards.getByRole("button", { name: /oscillator/i }).click();
  const add = sent.at(-1);
  expect(add).toMatchObject({ type: "add_layer", below: null });
  // The engine runs it: the cards close on the new layer.
  const layer = (add as unknown as { layer: { out: string } }).layer;
  receive({
    type: "aura",
    ...AURA,
    stack: {
      ...AURA.stack,
      layers: [...AURA.stack.layers, { id: layer.out, nodes: [{ id: layer.out, op: "osc", label: "Oscillator", in: [] }] }],
    },
  });
  await expect.element(screen.getByRole("region", { name: "add layer" })).not.toBeInTheDocument();
});

test("an example the engine did not take, refused or never sent, is not marked as playing", async () => {
  const { screen, answer } = await renderPanel();
  const looks = screen.getByRole("toolbar", { name: "looks" });
  await looks.getByRole("button", { name: "copper-tide" }).click();
  await answer(false);
  await expect.element(looks.getByRole("button", { name: "copper-tide" })).toHaveAttribute("aria-pressed", "false");
});

test("a bind that cuts to another look leaves no example marked", async () => {
  const { screen, answer, receive } = await renderPanel();
  const looks = screen.getByRole("toolbar", { name: "looks" });
  await looks.getByRole("button", { name: "copper-tide" }).click();
  await answer();
  await expect.element(looks.getByRole("button", { name: "copper-tide" })).toHaveAttribute("aria-pressed", "true");
  receive({ type: "status", error: "the look could not run on this arrangement (x), so tide runs", source: "bind", path: null });
  await expect.element(looks.getByRole("button", { name: "copper-tide" })).toHaveAttribute("aria-pressed", "false");
});

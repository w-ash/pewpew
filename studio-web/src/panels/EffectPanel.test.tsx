import type { ClientMessage, Sender, ServerMessage } from "@pewpew/page/wire";
import { WireContext, WireStore } from "@pewpew/page/wire";
import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { createQueryClient } from "@/api/queries";
import { MockAura } from "@/mocks/aura";
import { MOCK_LOOKS } from "@/mocks/looks";
import { EffectPanel } from "./EffectPanel";

/** The panel on a wire that holds the mock's `tide` and records what it sends; an `ask` settles at once. */
function renderPanel() {
  const store = new WireStore();
  store.opened({ gamma: 2.2, map: null });
  const aura = new MockAura(MOCK_LOOKS.tide);
  for (const msg of aura.states())
    store.receive(msg as unknown as ServerMessage);
  const sent: ClientMessage[] = [];
  const sender: Sender = {
    send: (msg) => sent.push(msg),
    sendLatest: (msg) => sent.push(msg),
    ask: async (msg) => {
      sent.push(msg);
    },
  };
  render(
    <QueryClientProvider client={createQueryClient()}>
      <WireContext.Provider value={{ store, sender }}>
        <EffectPanel />
      </WireContext.Provider>
    </QueryClientProvider>,
  );
  return { sent, store, aura };
}

describe("EffectPanel", () => {
  it("shows the example looks as the deck shows saved looks, and plays one whole, over its own fade", async () => {
    const { sent } = renderPanel();
    const looks = await screen.findByRole("toolbar", { name: "looks" });
    // The first nine, then the rest in the list of every look.
    expect(within(looks).getAllByRole("button")).toHaveLength(9);
    await userEvent.click(
      within(looks).getByRole("button", { name: "copper-tide" }),
    );
    expect(sent).toEqual([
      { type: "look", look: MOCK_LOOKS["copper-tide"], fade: null },
    ]);
    await waitFor(() =>
      expect(
        within(looks).getByRole("button", { name: "copper-tide" }),
      ).toHaveAttribute("aria-pressed", "true"),
    );
  });

  it("marks tide at the start, in the list of every look, until a surprise plays", async () => {
    const { sent } = renderPanel();
    await userEvent.click(
      await screen.findByRole("button", { name: /^all \d+ looks$/ }),
    );
    const all = screen.getByRole("region", { name: "looks" });
    const tide = within(all).getByRole("button", { name: "tide" });
    expect(tide).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(
      within(all).getByRole("button", { name: "warp-lane" }),
    );
    expect(sent.at(-1)).toEqual({
      type: "look",
      look: MOCK_LOOKS["warp-lane"],
      fade: null,
    });
    await waitFor(() =>
      expect(
        within(all).getByRole("button", { name: "warp-lane" }),
      ).toHaveAttribute("aria-pressed", "true"),
    );
    expect(tide).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(within(all).getByRole("button", { name: /close/ }));
    await userEvent.click(screen.getByRole("button", { name: /surprise me/ }));
    await userEvent.click(
      screen.getByRole("button", { name: /^all \d+ looks$/ }),
    );
    const again = screen.getByRole("region", { name: "looks" });
    expect(within(again).queryAllByRole("button", { pressed: true })).toEqual(
      [],
    );
  });

  it("shows the running look's main knobs and layers, and sets a knob by its address", async () => {
    const { sent } = renderPanel();
    // tide's front: its waves' frequency first.
    const freq = screen.getAllByRole("spinbutton", { name: /freq/i })[0];
    expect(freq).toBeDefined();
    expect(screen.getByRole("heading", { name: /^layers/ })).toBeVisible();
    for (const id of ["base", "echo", "sparks"])
      expect(screen.getAllByText(id).length).toBeGreaterThan(0);
    await userEvent.click(
      screen.getAllByRole("button", { name: /increase freq/i })[0],
    );
    expect(sent.at(-1)).toMatchObject({
      type: "set",
      name: "layers.base.waves.freq",
    });
  });

  it("asks for a surprise and a variation of what plays", async () => {
    const { sent } = renderPanel();
    await userEvent.click(screen.getByRole("button", { name: /surprise me/ }));
    await userEvent.click(screen.getByRole("button", { name: /vary this/ }));
    expect(sent).toEqual([
      { type: "surprise", seed: null },
      { type: "vary", strength: null, seed: null },
    ]);
  });

  it("adds a layer from the catalog's cards, above the one picked", async () => {
    const { sent, store, aura } = renderPanel();
    await userEvent.click(screen.getByRole("button", { name: "+ layer" }));
    const cards = screen.getByRole("region", { name: "add layer" });
    // Each shelf of cards starts folded but the first.
    for (const shelf of within(cards).getAllByRole("button", {
      expanded: false,
    }))
      await userEvent.click(shelf);
    const card = within(cards).getByRole("button", { name: /kaleidoscope/i });
    await userEvent.click(card);
    const add = sent.at(-1);
    expect(add).toMatchObject({ type: "add_layer", below: null });
    // The engine runs it: the cards close on the new layer.
    act(() => {
      aura.add((add as { layer: Record<string, unknown> }).layer, null);
      for (const msg of aura.states())
        store.receive(msg as unknown as ServerMessage);
    });
    expect(
      screen.queryByRole("button", { name: /kaleidoscope/i }),
    ).not.toBeInTheDocument();
  });
});

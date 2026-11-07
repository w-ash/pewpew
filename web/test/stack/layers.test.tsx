import { expect, test } from "vitest";
import { page, userEvent } from "vitest/browser";
import type { AuraState } from "../../src/aura/aura";
import type { LayerItem } from "../../src/stack/stack";
import type { ClientMessage, ServerMessage } from "../../src/wire/protocol";
import { App } from "../../src/app/App";
import { first, refused, AURA } from "../fixtures/messages";
import { pastDoubleTap, renderWired } from "../harness";

const records = first("declare").params as Record<string, unknown>[];
const values = first("params").values;
const zoo = AURA.stack.layers[0]!.nodes;
const aura = (patch: Partial<AuraState>): ServerMessage => ({ type: "aura", ...AURA, ...patch });

/** The look as the engine sends it with layers `ids`, bottom first, each running the zoo, as saved. */
function stacked(...ids: string[]): ServerMessage[] {
  const copy = <T,>(entries: [string, T][], id: string) =>
    entries.filter(([name]) => name.startsWith("layers.base.")).map(([name, v]): [string, T] => [name.replace("layers.base.", `layers.${id}.`), v]);
  const layered = ids.flatMap((id) => copy(records.map((r) => [String(r.name), { ...r, layer: id }]), id))
    .map(([name, r]) => ({ ...r, name }));
  const saved = Object.fromEntries([...ids.flatMap((id) => copy(Object.entries(values), id)), ...Object.entries(values).filter(([name]) => !name.startsWith("layers."))]);
  return [
    { type: "declare", params: [...layered, ...records.filter((r) => !String(r.name).startsWith("layers."))] },
    { type: "params", values: Object.fromEntries([...ids.flatMap((id) => copy(Object.entries(values), id)), ...Object.entries(values)]) },
    aura({ stack: { ...AURA.stack, layers: ids.map((id): LayerItem => ({ id, nodes: zoo })), routes: [], front: [] }, looks: { ...AURA.looks!, saved } }),
  ];
}

async function app(...ids: string[]) {
  const wired = await renderWired(<App />);
  for (const msg of stacked(...ids)) wired.receive(msg);
  return wired;
}

const last = (sent: ClientMessage[]) => sent.at(-1);
const focused = () => document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent;

test("a look of one layer has no layer chrome: its knobs under its heading, then a quiet + layer to the catalog; Esc closes it", async () => {
  const { screen } = await app("base");
  await expect.element(screen.getByRole("heading", { name: "base · 1 step" })).toBeVisible();
  await expect.element(screen.getByRole("heading", { name: /^layers/ })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: /^base/ })).not.toBeInTheDocument(); // no row
  await expect.element(screen.getByRole("switch", { name: "layer base" })).not.toBeInTheDocument();
  const add = screen.getByRole("button", { name: "+ layer" });
  await expect.element(add).toHaveAttribute("data-variant", "tertiary"); // quiet
  // Its knobs sit under its heading, before + layer: not after a list.
  const knob = document.querySelector('.lone-layer .param[data-param="layers.base.zoo.bands"]')!.getBoundingClientRect();
  expect(knob.bottom).toBeLessThan(add.element().getBoundingClientRect().top);
  await add.click();
  await expect.element(screen.getByRole("region", { name: "add layer" })).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "sources" })).toHaveFocus();
  await expect.element(screen.getByRole("textbox", { name: "look name" })).not.toBeInTheDocument(); // hidden under it
  await screen.getByRole("button", { name: "close add layer" }).click();
  await expect.element(screen.getByRole("button", { name: "+ layer" })).toHaveFocus();
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByRole("region", { name: "add layer" })).toBeVisible();
  await userEvent.keyboard("{Escape}");
  await expect.element(screen.getByRole("region", { name: "add layer" })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "+ layer" })).toHaveFocus();
});

test("a lone layer that runs a program heads its steps, folded, with no row, order, remove or mix", async () => {
  const { screen, receive } = await app("base");
  const program = [{ id: "waves", op: "osc", label: "Oscillator", in: [] }, { id: "tint", op: "palette", label: "Palette", in: ["waves"] }];
  receive(aura({ stack: { ...AURA.stack, layers: [{ id: "base", nodes: program }], routes: [], front: [] } }));
  await expect.element(screen.getByRole("heading", { level: 3, name: "base · 2 steps" })).toBeVisible();
  expect(document.querySelector(".chain")).toBeNull(); // its wiring would say no more than its steps
  await expect.element(screen.getByRole("button", { name: "move base up" })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "remove" })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("combobox", { name: "blend · base" })).not.toBeInTheDocument();
});

test("a lone layer's steps start folded to their titles, along its wiring, headed under the layer; the same caption in two says which", async () => {
  const { screen, receive } = await app("base");
  const program = [
    { id: "waves", op: "osc", label: "Oscillator", in: [] },
    { id: "drift", op: "noise", label: "Noise", in: [] },
    { id: "warp", op: "modulate", label: "Ripple", in: ["waves", "drift"] },
  ];
  const knob = (node: string) => ({ ...records.find((r) => r.name === "layers.base.zoo.level")!, name: `layers.base.${node}.level`, node });
  receive({ type: "declare", params: [knob("waves"), knob("drift"), knob("warp")] });
  receive(aura({ stack: { ...AURA.stack, layers: [{ id: "base", nodes: program }], routes: [], front: ["layers.base.warp.level"] } }));
  const titles = () => [...document.querySelectorAll(".lone-layer [data-part='item-trigger']")].map((t) => t.textContent);
  await expect.poll(titles).toEqual(["waves· oscillator", "drift· noise", "warp· ripple ← waves, drift"]);
  await expect.element(screen.getByRole("heading", { level: 4, name: /^waves/ })).toBeVisible(); // a step under its layer's h3
  await expect.element(screen.getByRole("button", { name: /^waves/ })).toHaveAttribute("aria-expanded", "false");
  await expect.element(screen.getByRole("slider", { name: "level · warp" })).toBeVisible(); // a main knob names its step
  localStorage.clear();
});

test("a lone layer's mix shows while it is off its defaults, so the page can put it back", async () => {
  const { screen, sent, receive } = await app("base");
  await expect.element(screen.getByRole("slider", { name: "opacity" })).not.toBeInTheDocument();
  receive({ type: "params", values: { "layers.base.opacity": 0.7, "layers.base.blend": "screen" } });
  const opacity = screen.getByRole("slider", { name: "opacity" });
  await expect.element(opacity).toHaveAttribute("aria-valuetext", "70%"); // a percent, as the brightness is
  await expect.element(screen.getByRole("spinbutton", { name: "opacity" })).toHaveValue("70");
  await screen.getByRole("combobox", { name: "blend" }).selectOptions("normal");
  expect(last(sent)).toEqual({ type: "set", name: "layers.base.blend", value: "normal" });
  receive({ type: "params", values: { "layers.base.blend": "normal" } });
  await expect.element(opacity).toBeVisible(); // the opacity is still off
  receive({ type: "params", values: { "layers.base.opacity": 1 } });
  await expect.element(screen.getByRole("slider", { name: "opacity" })).not.toBeInTheDocument();
});

test("a lone layer switched off shows its switch, and reset to defaults puts its whole mix back", async () => {
  const { screen, sent, receive } = await app("base");
  await expect.element(screen.getByRole("switch", { name: "enabled" })).not.toBeInTheDocument();
  receive({ type: "params", values: { "layers.base.enabled": false } });
  const on = screen.getByRole("switch", { name: "enabled" });
  await expect.element(on).not.toBeChecked();
  await on.click();
  expect(last(sent)).toEqual({ type: "set", name: "layers.base.enabled", value: true });
  receive({ type: "params", values: { "layers.base.opacity": 0.4 } });
  const from = sent.length;
  await screen.getByRole("button", { name: "reset to defaults" }).click();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to reset all" }).click();
  expect(sent.slice(from)).toEqual(expect.arrayContaining([
    { type: "set", name: "layers.base.enabled", value: true },
    { type: "set", name: "layers.base.opacity", value: 1 },
    { type: "set", name: "layers.base.blend", value: "normal" },
  ]));
  receive({ type: "params", values: { "layers.base.enabled": true, "layers.base.opacity": 1 } });
  await expect.element(screen.getByRole("switch", { name: "enabled" })).not.toBeInTheDocument();
});

test("the open row opens under its name, its knobs starting where the name does, not after the list", async () => {
  const { screen } = await app("base", "top");
  await screen.getByRole("button", { name: "top zoo", exact: true }).click();
  const card = document.querySelector<HTMLElement>(".layer:has(> .layer-body)")!;
  await expect.poll(() => card?.querySelector('[role="slider"][aria-labelledby]')).not.toBeNull();
  expect(getComputedStyle(card).backgroundColor).toBe("rgba(0, 0, 0, 0)"); // one cue of nesting: no card, the indent
  const knobs = [...card.querySelectorAll(".layer-body .param")];
  expect(knobs.length).toBeGreaterThan(0);
  const name = card.querySelector(".layer-id")!.getBoundingClientRect();
  const own = [...card.querySelectorAll(".layer-body > .param")];
  expect(own.length).toBeGreaterThan(0);
  expect(own.every((k) => Math.round(k.getBoundingClientRect().left) === Math.round(name.left))).toBe(true);
  const base = screen.getByRole("button", { name: "base zoo", exact: true }).element().getBoundingClientRect();
  expect(knobs.every((k) => k.getBoundingClientRect().bottom <= base.top)).toBe(true); // the next row comes after them
});

test("a mix knob the look lists in front shows there too; with a mouse its row's slider is its one home in the stack", async () => {
  const { screen, receive, sent } = await app("base", "top");
  receive(aura({ stack: { ...AURA.stack, layers: ["base", "top"].map((id) => ({ id, nodes: zoo })), routes: [], front: ["layers.top.opacity"] } }));
  receive({ type: "params", values: { "layers.top.opacity": 0.6, "layers.top.blend": "screen", "layers.base.opacity": 0.5 } });
  await screen.getByRole("button", { name: "top zoo (changed)" }).click();
  await expect.poll(() => document.querySelectorAll('[role="slider"][aria-labelledby]').length).toBeGreaterThan(1);
  const opacities = [...document.querySelectorAll<HTMLElement>('[role="slider"]')].filter((el) => el.getAttribute("aria-valuetext") === "60%");
  expect(opacities).toHaveLength(2); // the front knob, as the author chose, and the row's head; the open row holds the blend alone
  await expect.element(screen.getByRole("combobox", { name: "blend · top" })).toBeVisible();
  expect([...document.querySelectorAll(".mix-glance")].map((el) => el.textContent)).toEqual(["screen · 60%", "50%"]);
  // The rows' sliders and readouts share columns, whatever each readout says.
  const edges = (sel: string) => new Set([...document.querySelectorAll(sel)].map((el) => Math.round(el.getBoundingClientRect().right)));
  expect([edges(".mix-opacity").size, edges(".mix-glance > .readout").size]).toEqual([1, 1]);
  // Each row's head sets its layer's opacity, so layers balance with no row open.
  screen.getByRole("slider", { name: "opacity · base" }).element().focus();
  await userEvent.keyboard("{ArrowLeft}");
  expect(last(sent)).toEqual({ type: "set", name: "layers.base.opacity", value: 0.495 });
});

test("for assistive tech the look is one region under its title: its blocks h3, its layer rows h4", async () => {
  const { screen } = await app("base", "top");
  const look = screen.getByRole("region", { name: "warm" });
  await expect.element(look.getByRole("heading", { level: 3, name: "layers · top first" })).toBeVisible();
  await expect.element(look.getByRole("heading", { level: 4, name: "top zoo" })).toBeVisible();
});

test("a row says so while a knob of its layer is off the look as saved", async () => {
  const { screen, receive } = await app("base", "top");
  await expect.element(screen.getByRole("button", { name: "top zoo", exact: true })).toBeVisible();
  receive({ type: "params", values: { "layers.top.zoo.level": 0.7 } });
  await expect.element(screen.getByRole("button", { name: "top zoo (changed)", exact: true })).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "base zoo", exact: true })).toBeVisible();
});

test("the layers list the top one first; the picked row's mix goes to its layer", async () => {
  const { screen, sent, receive } = await app("base", "top");
  const rows = [...document.querySelectorAll(".layer .layer-id")].map((el) => el.textContent);
  expect(rows).toEqual(["top", "base"]);
  await expect.element(screen.getByRole("heading", { name: "layers · top first" })).toBeVisible();
  // Several layers start with their rows closed, so the stack reads at a glance.
  await expect.element(screen.getByRole("button", { name: "top zoo" })).toHaveAttribute("aria-expanded", "false");
  await screen.getByRole("button", { name: "top zoo" }).click();
  await expect.element(screen.getByRole("button", { name: "top zoo" })).toHaveAttribute("aria-expanded", "true");
  await screen.getByRole("switch", { name: "layer base" }).click();
  expect(last(sent)).toEqual({ type: "set", name: "layers.base.enabled", value: false });
  screen.getByRole("slider", { name: "opacity · top" }).last().element().focus(); // in its row; the look shows it in front too
  await userEvent.keyboard("{ArrowLeft}");
  expect(last(sent)).toEqual({ type: "set", name: "layers.top.opacity", value: 0.995 });
  await screen.getByRole("combobox", { name: "blend · top" }).selectOptions("screen");
  expect(last(sent)).toEqual({ type: "set", name: "layers.top.blend", value: "screen" });
  receive({ type: "status", error: "layers.base.zoo.render raised: boom", source: "render", path: "layers.base.zoo" });
  await expect.element(screen.getByRole("button", { name: "base zoo failed" })).toBeVisible();
  // Picking the other row shows its controls and its knobs instead.
  await screen.getByRole("button", { name: "base zoo failed" }).click();
  await expect.element(screen.getByRole("slider", { name: "level · base" }).last()).toBeVisible(); // its knobs in its row
  screen.getByRole("slider", { name: "opacity · base" }).element().focus();
  await userEvent.keyboard("{ArrowLeft}");
  expect(last(sent)).toEqual({ type: "set", name: "layers.base.opacity", value: 0.995 });
});

test("a blend's ? says what the chosen mode does when asked, every other mode behind all modes", async () => {
  const { screen, receive } = await app("base", "top");
  receive({ type: "params", values: { "layers.top.blend": "screen" } });
  await screen.getByRole("button", { name: "top zoo (changed)" }).click();
  const about = screen.getByRole("button", { name: "about blend · top" });
  await expect.element(screen.getByText(/Adds light without washing out to white/)).not.toBeInTheDocument();
  await about.click();
  await expect.element(about).toHaveAttribute("aria-expanded", "true");
  const select = screen.getByRole("combobox", { name: "blend · top" });
  await expect.element(select).toHaveAccessibleDescription(/^screen: Adds light without washing out to white/);
  const multiply = screen.getByText(/multiply: Darkens what is below/);
  await expect.element(multiply).not.toBeVisible();
  await screen.getByText("all modes").click();
  await expect.element(multiply).toBeVisible();
  about.element().focus(); // WebKit focuses no button on a click
  await userEvent.keyboard("{Escape}");
  await expect.element(about).toHaveAttribute("aria-expanded", "false");
});

test("▲ and ▼ move a layer one place, off at the ends, and keep focus in its new place", async () => {
  const { screen, sent, receive } = await app("base", "top");
  await screen.getByRole("button", { name: "top zoo" }).click();
  await expect.element(screen.getByRole("button", { name: "move top up" })).toBeDisabled();
  await screen.getByRole("button", { name: "move top down" }).click();
  expect(last(sent)).toEqual({ type: "move_layer", lid: "top", to: 0 });
  for (const msg of stacked("top", "base")) receive(msg);
  await expect.poll(() => [...document.querySelectorAll(".layer .layer-id")].map((el) => el.textContent)).toEqual(["base", "top"]);
  await expect.element(screen.getByRole("button", { name: "move top down" })).toBeDisabled();
  await expect.element(screen.getByRole("button", { name: "top zoo" })).toHaveAttribute("aria-expanded", "true");
  await expect.poll(focused).toBe("move top up"); // its own button, now that ▼ is off
});

test("Alt+↑ and Alt+↓ on a row move its layer; its row keeps focus", async () => {
  const { screen, sent, receive } = await app("base", "mid", "top");
  const row = screen.getByRole("button", { name: "mid zoo" });
  await row.click();
  await expect.element(row).toHaveAttribute("aria-keyshortcuts", "Alt+ArrowUp Alt+ArrowDown");
  await userEvent.keyboard("{Alt>}{ArrowUp}{/Alt}");
  expect(last(sent)).toEqual({ type: "move_layer", lid: "mid", to: 2 });
  await expect.element(row).toHaveFocus(); // not the arrow keys' move to the next row
  for (const msg of stacked("base", "top", "mid")) receive(msg);
  await expect.poll(() => document.querySelector(".layer .layer-id")?.textContent).toBe("mid");
  await expect.element(row).toHaveFocus();
  await expect.element(screen.getByRole("status").filter({ hasText: "mid moved to 1 of 3, top first" })).toBeInTheDocument();
  await userEvent.keyboard("{Alt>}{ArrowDown}{/Alt}");
  expect(last(sent)).toEqual({ type: "move_layer", lid: "mid", to: 1 });
  await userEvent.keyboard("{ArrowDown}");
  await expect.element(screen.getByRole("button", { name: "top zoo" })).toHaveFocus(); // plain arrows move focus
});

test("remove takes two presses; focus goes to the next row, or to + layer when one is left", async () => {
  const { screen, sent, receive } = await app("base", "mid", "top");
  await screen.getByRole("button", { name: "mid zoo" }).click();
  await screen.getByRole("button", { name: "remove" }).click();
  expect(sent.filter((m) => m.type === "remove_layer")).toEqual([]);
  await expect.element(screen.getByRole("status").filter({ hasText: "remove mid? press again to confirm" })).toBeInTheDocument();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to remove" }).click();
  expect(last(sent)).toEqual({ type: "remove_layer", lid: "mid" });
  for (const msg of stacked("base", "top")) receive(msg);
  await expect.element(screen.getByRole("button", { name: "base zoo" })).toHaveFocus();
  await expect.element(screen.getByRole("button", { name: "base zoo" })).toHaveAttribute("aria-expanded", "true");
  await expect.element(screen.getByRole("status").filter({ hasText: "mid removed" })).toBeInTheDocument();
  await screen.getByRole("button", { name: "remove" }).click();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to remove" }).click();
  expect(last(sent)).toEqual({ type: "remove_layer", lid: "base" });
  for (const msg of stacked("top")) receive(msg);
  await expect.element(screen.getByRole("button", { name: "+ layer" })).toHaveFocus();
  receive(refused("remove_layer", "a look has at least one layer"));
  await expect.poll(() => document.querySelector(".status-bar")?.textContent).toBe("a look has at least one layer");
});

test("a card adds its example screened over the look, then its row opens with focus", async () => {
  const { screen, sent, receive } = await app("base");
  await screen.getByRole("button", { name: "+ layer" }).click();
  const osc = screen.getByRole("button", { name: "Oscillator", exact: true });
  await expect.element(osc).toHaveAccessibleDescription("Stripes along one axis that travel across the room");
  await osc.click();
  expect(last(sent)).toEqual({
    type: "add_layer", below: null,
    layer: { out: "osc", nodes: { osc: { op: "osc", args: { freq: 8, sync: 0.1 } } }, blend: "screen", opacity: 0.7 },
  });
  await expect.element(osc).toHaveAttribute("data-busy");
  for (const msg of stacked("base", "osc")) receive(msg);
  await expect.element(screen.getByRole("region", { name: "add layer" })).not.toBeInTheDocument();
  const row = screen.getByRole("button", { name: "osc zoo" });
  await expect.element(row).toHaveFocus();
  await expect.element(row).toHaveAttribute("aria-expanded", "true");
});

test("a card adds its layer right above the picked one, as the title says; a second press while it waits adds none", async () => {
  const { screen, sent } = await app("base", "top");
  await screen.getByRole("button", { name: "base zoo" }).click();
  await screen.getByRole("button", { name: "+ layer" }).click();
  await expect.element(screen.getByRole("region", { name: "add above base" })).toBeVisible();
  const osc = screen.getByRole("button", { name: "Oscillator", exact: true });
  await osc.dblClick();
  expect(sent.filter((m) => m.type === "add_layer")).toEqual([expect.objectContaining({ below: "top" })]);
  await expect.element(osc).toHaveAttribute("aria-disabled", "true");
});

test("Esc closes the catalog after a press on its empty ground", async () => {
  const { screen } = await app("base");
  await screen.getByRole("button", { name: "+ layer" }).click();
  const panel = screen.getByRole("region", { name: "add layer" });
  const { height } = panel.element().getBoundingClientRect();
  await panel.click({ position: { x: 2, y: height - 2 } });
  await userEvent.keyboard("{Escape}");
  await expect.element(panel).not.toBeInTheDocument();
});

test("while a cue holds a look the open catalog waits, inert, and says why, as the editor does", async () => {
  const { screen, receive } = await app("base");
  await screen.getByRole("button", { name: "+ layer" }).click();
  const panel = screen.getByRole("region", { name: "add layer" });
  await expect.element(screen.getByRole("button", { name: "Oscillator", exact: true })).toBeVisible();
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, held: { trigger: "door", look: "cool", until: 9 } } }));
  await expect.element(panel.getByText("door is playing cool: add a layer when it ends")).toBeVisible();
  expect(document.querySelector(".shelves")?.hasAttribute("inert")).toBe(true);
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, held: null } }));
  await expect.element(panel.getByText("door is playing cool: add a layer when it ends")).not.toBeInTheDocument();
  expect(document.querySelector(".shelves")?.hasAttribute("inert")).toBe(false);
});

test("a card the map cannot run says why; once it can, a press adds its example; a refusal shows there", async () => {
  const { screen, sent, receive } = await app("base");
  await screen.getByRole("button", { name: "+ layer" }).click();
  await screen.getByRole("button", { name: "space" }).click();
  const kaleid = screen.getByRole("button", { name: "Kaleidoscope" });
  await expect.element(kaleid).toBeDisabled();
  await expect.element(kaleid).toHaveAccessibleDescription("a strip has no plane to fold; use mirror along the strip");
  receive(aura({ stack: { ...AURA.stack, dims: 2 } }));
  await expect.element(kaleid).toBeEnabled();
  await kaleid.click();
  expect(last(sent)).toMatchObject({ type: "add_layer", layer: { blend: "screen", opacity: 0.7 } });
  receive(refused("add_layer", "layers.palette: the map went away"));
  await expect.element(screen.getByRole("alert")).toHaveTextContent("layers.palette: the map went away");
  await expect.element(screen.getByRole("region", { name: "add layer" })).toBeVisible();
});

test("a card whose own example the map cannot run says so; one that reads the layers below is an effect on them", async () => {
  const { screen, sent, receive } = await app("base");
  const { cards, blends } = first("catalog");
  const kaleid = cards[1]!;
  const folded = { ...kaleid.examples[0]!, py: "noise(3).kaleid(5)", dims: [2, 3] };
  const tinted = {
    py: "osc(8).hue(60)", dims: [1, 2, 3],
    json: { out: "hue", nodes: { osc: { op: "osc", args: { freq: 8 } }, hue: { op: "hue", in: ["osc"], args: { amount: 60 } } } },
  };
  const shape = { ...kaleid, name: "shape", label: "Shape", sig: "source", dims: [1, 2, 3], fix: "", examples: [folded, tinted] };
  receive({ type: "catalog", blends, cards: [shape] });
  await screen.getByRole("button", { name: "+ layer" }).click(); // sources, open
  const card = screen.getByRole("button", { name: "Shape" });
  await expect.element(card).toBeDisabled();
  await expect.element(card).toHaveAccessibleDescription("its example needs a map of 2 or 3 dimensions");
  const below = { py: "below().hue(90)", dims: [1, 2, 3], json: { out: "hue", nodes: { below: { op: "below" }, hue: { op: "hue", in: ["below"] } } } };
  receive({ type: "catalog", blends, cards: [{ ...kaleid, name: "hue", label: "Hue", sig: "color", dims: [1, 2, 3], fix: "", examples: [tinted, below] }] });
  await screen.getByRole("button", { name: "effects on the layers below" }).click();
  await screen.getByRole("button", { name: "Hue" }).click();
  expect(last(sent)).toMatchObject({ type: "add_layer", layer: below.json }); // it acts on them as they are: normal, at 1
});

test("on a phone the layer rows fit, and every target is a touch's size", async () => {
  await page.viewport(390, 844);
  await app("base", "top");
  const slot = document.querySelector<HTMLElement>(".slot")!;
  expect(slot.scrollWidth).toBeLessThanOrEqual(slot.clientWidth);
  // A reset dot is drawn small; its hit area, a target, is its ::after.
  const small = [...document.querySelectorAll<HTMLElement>(".layers button:not(.reset-dot), .layers select, .layer-on")]
    .filter((el) => el.checkVisibility())
    .map((el) => el.getBoundingClientRect())
    .filter((r) => r.height < 24);
  expect(small).toEqual([]);
  await page.viewport(414, 896);
});

test("on the bottom layer the blends that show black over nothing say so, and its ? says why", async () => {
  const { screen } = await app("base", "top");
  await screen.getByRole("button", { name: "base zoo" }).click();
  const blend = screen.getByRole("combobox", { name: "blend · base" });
  const options = [...blend.element().querySelectorAll("option")].map((o) => o.textContent);
  expect(options).toContain("multiply (black: nothing below)");
  expect(options).toContain("screen");
  await screen.getByRole("button", { name: "base zoo" }).click();
  await screen.getByRole("button", { name: "top zoo" }).click();
  const above = [...screen.getByRole("combobox", { name: "blend · top" }).element().querySelectorAll("option")].map((o) => o.textContent);
  expect(above).toContain("multiply");
});

test("▲ that moves a layer to the top hands focus to its ▼; a press on + layer at the cap says why", async () => {
  const { screen, receive } = await app("base", "top");
  await screen.getByRole("button", { name: "base zoo" }).click();
  screen.getByRole("button", { name: "move base up" }).element().focus();
  await userEvent.keyboard("{Enter}");
  for (const msg of stacked("top", "base")) receive(msg);
  await expect.poll(focused).toBe("move base down");
  const many = Array.from({ length: 16 }, (_, i) => `l${i}`);
  for (const msg of stacked(...many)) receive(msg);
  (screen.getByRole("button", { name: "+ layer" }).element() as HTMLElement).click();
  await expect.element(screen.getByText("a look has at most 16 layers; remove one first")).toBeVisible();
  await expect.element(screen.getByRole("region", { name: "add layer" })).not.toBeInTheDocument();
});


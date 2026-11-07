import { act } from "react";
import { expect, test } from "vitest";
import { page, userEvent } from "vitest/browser";
import { App } from "../../src/app/App";
import { board, health, hello } from "../fixtures/messages";
import { pastDoubleTap, renderWired } from "./harness";

const NO_ROOM = "layout tools need a room map (start the run with --room)";

test("on a phone the layout tools take the editor's place, and the deck stays", async () => {
  const { screen } = await renderWired(<App />);
  const toggle = screen.getByRole("button", { name: "layout" });
  await expect.element(screen.getByText(NO_ROOM)).not.toBeInTheDocument();
  await toggle.click();
  await expect.element(screen.getByText(NO_ROOM)).toBeVisible();
  await expect.element(screen.getByRole("switch", { name: "invert" })).not.toBeInTheDocument(); // the editor's
  await expect.element(screen.getByRole("button", { name: "blackout" })).toBeVisible();
  await userEvent.keyboard("l");
  await expect.element(screen.getByText(NO_ROOM)).not.toBeInTheDocument();
});

test("wide, the layout tools sit under the canvas beside the editor", async () => {
  await page.viewport(1280, 800);
  const { screen } = await renderWired(<App />);
  await screen.getByRole("button", { name: "layout" }).click();
  await expect.element(screen.getByText(NO_ROOM)).toBeVisible();
  await expect.element(screen.getByRole("switch", { name: "invert" })).toBeVisible(); // the editor's
  await page.viewport(414, 896);
});

test("wide, the canvas and the side panel fill the page under the top bar, never past its foot", async () => {
  await page.viewport(1280, 800);
  await renderWired(<App />);
  const foot = document.querySelector(".app")!.getBoundingClientRect().bottom;
  const split = document.querySelector('[data-scope="splitter"][data-part="root"]')!.getBoundingClientRect();
  expect([Math.round(split.top), Math.round(split.bottom)]).toEqual([Math.round(document.querySelector(".head")!.getBoundingClientRect().bottom), Math.round(foot)]);
  await page.viewport(414, 896);
});

test("the health panel opens in the slot, so blackout stays in reach", async () => {
  const { screen, receive } = await renderWired(<App />);
  receive({ type: "health", ...health([board({ level: "bad", reasons: ["unreachable"] })], { level: "bad" }) });
  await screen.getByRole("button", { name: /Board A: unreachable/ }).click();
  const panel = screen.getByRole("region", { name: "aura health" });
  await expect.element(panel).toBeVisible();
  const blackout = screen.getByRole("button", { name: "blackout" });
  await expect.element(blackout).toBeVisible();
  const [p, b] = [panel.element().getBoundingClientRect(), blackout.element().getBoundingClientRect()];
  expect(b.top >= p.bottom || b.bottom <= p.top).toBe(true);
  await screen.getByRole("button", { name: "close aura health" }).click();
  await expect.element(panel).not.toBeInTheDocument();
});

test("an opened panel takes focus to its title, so Esc closes it, and hands focus back", async () => {
  const { screen, receive } = await renderWired(<App />);
  receive({ type: "health", ...health([board({})]) });
  const chip = screen.getByRole("button", { name: /aura health/ });
  chip.element().focus();
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByRole("heading", { name: "aura health" })).toHaveFocus();
  await userEvent.keyboard("{Escape}");
  await expect.element(screen.getByRole("region", { name: "aura health" })).not.toBeInTheDocument();
  await expect.element(chip).toHaveFocus();
});

test("the editor keeps a typed name and its toggles while a panel covers it", async () => {
  const { screen, receive } = await renderWired(<App />);
  receive({ type: "health", ...health([board({})]) });
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "save as new…" }).click();
  await screen.getByRole("textbox", { name: "look name" }).fill("draft");
  await screen.getByRole("switch", { name: /^include brightness \d+%$/ }).click();
  await screen.getByRole("button", { name: /aura health/ }).click();
  await expect.element(screen.getByRole("region", { name: "aura health" })).toBeVisible();
  expect(document.querySelector<HTMLElement>(".look-name")?.checkVisibility()).toBe(false);
  await screen.getByRole("button", { name: "close aura health" }).click();
  await expect.element(screen.getByRole("textbox", { name: "look name" })).toHaveValue("draft");
  await expect.element(screen.getByRole("switch", { name: /^include brightness \d+%$/ })).not.toBeChecked();
});

test("find boards is offered only by an aura that streams to boards", async () => {
  const { screen, receive } = await renderWired(<App />);
  receive({ type: "health", ...health([]) });
  await screen.getByRole("button", { name: /aura health/ }).click();
  await expect.element(screen.getByText("rendering")).toBeVisible();
  expect(screen.getByRole("button", { name: "find boards" }).query()).toBeNull();
  receive({ type: "health", ...health([board({})]) });
  await expect.element(screen.getByRole("button", { name: "find boards" })).toBeVisible();
});

test("a found board is offered to the lost board it is, without layout mode", async () => {
  const { screen, sent, receive } = await renderWired(<App />);
  const found = { address: "192.168.1.77", mac: "aabbccddeeff", name: "WLED", ver: "16.0.1", live: false, lm: null, lip: null, board: "A", at: null };
  const scan = { running: false, subnet: "192.168.1.0/24", found: [found], error: null };
  receive({ type: "health", ...health([board({ level: "bad", lost: true, reasons: ["unreachable"] })], { level: "bad", scan }) });
  await screen.getByRole("button", { name: /Board A/ }).click();
  await screen.getByRole("button", { name: "use for A" }).click();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to use for A" }).click();
  expect(sent.at(-1)).toEqual({ type: "rebind", board: "A", address: "192.168.1.77" });
});

test("a lost connection makes every control inert and says so, disarms, and gives focus back once it returns", async () => {
  const { screen, store, sent } = await renderWired(<App />);
  screen.getByRole("button", { name: "blackout" }).element().focus(); // WebKit focuses no button on a click
  await userEvent.keyboard("{Enter}");
  act(() => store.disconnected());
  await expect.element(screen.getByText(/^Lost pewpew\. Retrying…$/)).toBeVisible(); // on the engine's own laptop
  await expect.poll(() => document.querySelector(".blackout")?.hasAttribute("data-armed")).toBe(false);
  expect([".slot", ".deck", ".stage-live"].map((part) => !!document.querySelector(part)?.closest("[inert]"))).toEqual([true, true, true]);
  await userEvent.keyboard("b");
  expect(document.querySelector(".blackout")?.hasAttribute("data-armed")).toBe(false);
  expect(sent).toEqual([]);
  act(() => store.receive(hello()));
  await expect.element(screen.getByRole("button", { name: "blackout" })).toHaveFocus();
});

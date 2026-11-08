// The Console page under a Gallery session's hello: every feature shows by the hello's capabilities, or by
// state the Gallery never sends, so the Gallery's page is read-only and has none of the engine's tools.
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { App } from "../../src/app/App";
import { EMPTY_ARRANGEMENT, useDoc } from "../../src/arrange/doc";
import { createHistory } from "../../src/arrange/history";
import { PARTS_URL } from "../../src/rig/loadParts";
import type { ServerMessage } from "../../src/wire/protocol";
import { first, galleryGreeting, GREETING, LATER } from "../fixtures/messages";
import { renderWired } from "../harness";
import { partsCatalog } from "../rig3d/rig";

const realFetch = globalThis.fetch;

beforeEach(() => {
  useDoc.setState({ history: createHistory(EMPTY_ARRANGEMENT), selection: null, loads: 0, readOnly: false });
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) =>
    input === PARTS_URL ? Response.json(partsCatalog) : realFetch(input, init),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** The engine's arrangement run, which takes `arrange` and has boards. */
const CONSOLE_RUN: readonly ServerMessage[] = [...GREETING, first("layout", LATER)];

test("a Gallery hello hides the health chip, layout mode and its key, the editor and Publish, and shows the banner", async () => {
  const { screen, receive } = await renderWired(<App />, galleryGreeting());
  await expect.element(screen.getByRole("status").filter({ hasText: "Shared layout · read-only" })).toBeVisible();
  await expect.element(screen.getByRole("heading", { level: 1, name: "pewpew Gallery" })).toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "layout" })).not.toBeInTheDocument();
  expect(document.querySelector(".health-chip")).toBeNull();
  // The L key opens no layout tools, and the `?` list does not offer it.
  await userEvent.keyboard("l");
  await expect.element(screen.getByRole("region", { name: "layout" })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "blink" })).not.toBeInTheDocument();
  await screen.getByRole("button", { name: "keyboard shortcuts" }).click();
  await expect.element(screen.getByRole("dialog")).toBeVisible();
  await expect.element(screen.getByText("layout tools on or off")).not.toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  // A health message, which the Gallery never sends, would not make it the engine's page.
  receive(first("health"));
  await expect.element(screen.getByRole("button", { name: "layout" })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "publish" })).not.toBeInTheDocument();
});

test("the Gallery shows its rig in 3D first, and its 3D view never edits", async () => {
  const { screen } = await renderWired(<App />, galleryGreeting());
  await expect.element(screen.getByRole("img", { name: "3D preview of the LEDs" })).toBeInTheDocument();
  await expect.element(screen.getByRole("radio", { name: "3D" })).toBeChecked();
  await screen.getByRole("img", { name: "3D preview of the LEDs" }).click();
  expect(useDoc.getState().selection).toBeNull();
  await screen.getByRole("radiogroup", { name: "Stage view" }).getByText("2D", { exact: true }).click();
  await expect.element(screen.getByRole("img", { name: "preview of the LEDs", exact: true })).toBeInTheDocument();
});

test("the engine's page is the Console: its name, flat first, layout mode, the health chip, and no banner", async () => {
  const { screen } = await renderWired(<App />, CONSOLE_RUN);
  await expect.element(screen.getByRole("heading", { level: 1, name: "pewpew Console" })).toBeInTheDocument();
  await expect.element(screen.getByRole("img", { name: "preview of the LEDs", exact: true })).toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "layout" })).toBeVisible();
  expect(document.querySelector(".health-chip")).not.toBeNull();
  await expect.element(screen.getByText("Shared layout · read-only")).not.toBeInTheDocument();
});

import { useState } from "react";
import { expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { useShortcuts } from "../../src/design/shortcuts";
import { ParamField } from "../../src/params/ParamField";
import { ShortcutHelp } from "../../src/status/ShortcutHelp";
import { param } from "../fixtures/describe";
import { renderWired } from "./harness";

test("Esc runs its shortcut and still closes the open list, and focus goes back", async () => {
  const disarm = vi.fn();
  function Page() {
    const [open, setOpen] = useState(false);
    useShortcuts([{ hotkey: "Escape", label: "disarm a two-press button", keys: "Esc", action: disarm }]);
    return (
      <>
        <button type="button" onClick={() => setOpen(true)}>
          help
        </button>
        <ShortcutHelp open={open} onClose={() => setOpen(false)} />
      </>
    );
  }
  const screen = await render(<Page />);
  // From the keyboard: WebKit does not focus a clicked button, so focus would go back to the page.
  screen.getByRole("button", { name: "help" }).element().focus();
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByRole("dialog", { name: "keyboard shortcuts" })).toBeVisible();
  // The keys a focused control takes are listed too: the looks' arrows, a layer's move, a knob's reset.
  for (const keys of ["← → Home End", "Alt+↑ ↓", "Backspace"]) await expect.element(screen.getByText(keys, { exact: true })).toBeVisible();
  await userEvent.keyboard("{Escape}");
  expect(disarm).toHaveBeenCalledTimes(1);
  await expect.element(screen.getByRole("dialog")).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "help" })).toHaveFocus();
});

test("a key on a focused param is the param's, and the list turns single keys off", async () => {
  const press = vi.fn();
  function Page() {
    const [open, setOpen] = useState(false);
    useShortcuts([{ hotkey: "2", label: "two", action: press }]);
    return (
      <>
        <ParamField p={param("zoo_test", "level")} />
        <button type="button" onClick={() => setOpen(true)}>
          help
        </button>
        <ShortcutHelp open={open} onClose={() => setOpen(false)} />
      </>
    );
  }
  const { screen } = await renderWired(<Page />);
  screen.getByRole("slider", { name: "level" }).element().focus();
  await userEvent.keyboard("2");
  expect(press).not.toHaveBeenCalled();
  await screen.getByRole("button", { name: "help" }).click();
  await screen.getByRole("switch", { name: "single-key shortcuts" }).click();
  await expect.element(screen.getByRole("dialog", { name: "keyboard shortcuts" })).toBeVisible();
  await userEvent.keyboard("{Escape}");
  (document.activeElement as HTMLElement).blur();
  await userEvent.keyboard("2");
  expect(press).not.toHaveBeenCalled();
  await screen.getByRole("button", { name: "help" }).click();
  await screen.getByRole("switch", { name: "single-key shortcuts" }).click();
  await userEvent.keyboard("{Escape}");
  // Closing the list puts focus back on the slider in WebKit, where the click left it.
  (document.activeElement as HTMLElement).blur();
  await userEvent.keyboard("2");
  expect(press).toHaveBeenCalledTimes(1);
});

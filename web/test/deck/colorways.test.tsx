import { expect, test } from "vitest";
import { userEvent } from "vitest/browser";
import type { AuraState } from "../../src/aura/aura";
import { LookPanel } from "../../src/deck/LookPanel";
import { StatusBar } from "../../src/status/StatusBar";
import { AURA, refused } from "../fixtures/messages";
import { renderWired } from "../harness";

const stack = (patch: Partial<AuraState["stack"]>) => ({ type: "aura" as const, ...AURA, stack: { ...AURA.stack, ...patch } });

test("the look's colorways are chips above its knobs, the active one pressed, and a press sends the colorway", async () => {
  const { screen, sent, receive } = await renderWired(<LookPanel />);
  const chips = screen.getByRole("toolbar", { name: "colorways" });
  const green = chips.getByRole("button", { name: "green" });
  const red = chips.getByRole("button", { name: "red" });
  await expect.element(green).toHaveAttribute("aria-pressed", "true");
  await expect.element(red).toHaveAttribute("aria-pressed", "false");
  // In the look's block, under its forms and above its main knobs.
  const row = chips.element().closest(".look-block > .colorways");
  expect(row?.previousElementSibling?.classList.contains("look-forms")).toBe(true);
  await red.click();
  expect(sent).toEqual([{ type: "colorway", name: "red" }]);
  receive(stack({ colorway: "red" }));
  await expect.element(red).toHaveAttribute("aria-pressed", "true");
  await expect.element(green).toHaveAttribute("aria-pressed", "false");
  // A knob turned by hand leaves no colorway active.
  receive(stack({ colorway: null }));
  await expect.element(red).toHaveAttribute("aria-pressed", "false");
});

test("24 colorways wrap onto lines inside a phone's column, every chip in reach", async () => {
  const names = Array.from({ length: 24 }, (_, i) => (i % 3 ? `colorway ${i}` : `a long colorway name ${i}`));
  const { screen, receive } = await renderWired(
    <div style={{ width: "358px" }}>
      <LookPanel />
    </div>,
  );
  receive(stack({ colorways: names, colorway: names[5]! }));
  const chips = screen.getByRole("toolbar", { name: "colorways" });
  await expect.element(chips.getByRole("button", { name: names[23]! })).toBeVisible();
  const group = chips.element().getBoundingClientRect();
  const boxes = [...chips.element().querySelectorAll("button")].map((b) => b.getBoundingClientRect());
  expect(boxes).toHaveLength(24);
  for (const box of boxes) {
    expect(box.left).toBeGreaterThanOrEqual(group.left - 0.5);
    expect(box.right).toBeLessThanOrEqual(group.right + 0.5);
  }
  expect(new Set(boxes.map((b) => Math.round(b.top))).size).toBeGreaterThan(3);
});

test("a look with no colorways shows no row", async () => {
  const { screen, receive } = await renderWired(<LookPanel />);
  receive(stack({ colorways: [], colorway: null }));
  await expect.element(screen.getByRole("toolbar", { name: "colorways" })).not.toBeInTheDocument();
});

const looks = (patch: Partial<NonNullable<AuraState["looks"]>>) => ({ type: "aura" as const, ...AURA, looks: { ...AURA.looks!, ...patch } });

test("drift, at the row's head, shows and switches the current look's colorway drift", async () => {
  const { screen, sent, receive } = await renderWired(<LookPanel />);
  const current = AURA.looks!.current!;
  const drift = screen.getByRole("button", { name: "drift" });
  await expect.element(drift).toHaveAttribute("aria-pressed", "false");
  expect(drift.element().closest(".colorways > .param-head")).not.toBeNull();
  await drift.click();
  expect(sent).toEqual([{ type: "drift", name: current, on: true }]);
  receive(looks({ items: AURA.looks!.items.map((item) => ({ ...item, drift: item.name === current })) }));
  await expect.element(drift).toHaveAttribute("aria-pressed", "true");
  await drift.click();
  expect(sent.at(-1)).toEqual({ type: "drift", name: current, on: false });
});

test("drift is offered only for a saved look with 2 colorways or more", async () => {
  const { screen, receive } = await renderWired(<LookPanel />);
  const drift = screen.getByRole("button", { name: "drift" });
  await expect.element(drift).toBeInTheDocument();
  receive(stack({ colorways: ["green"], colorway: "green" }));
  await expect.element(drift).not.toBeInTheDocument();
  receive(stack({ colorways: ["green", "red"], colorway: "green" }));
  await expect.element(drift).toBeInTheDocument();
  receive(looks({ made: "surprise 7" }));
  await expect.element(drift).not.toBeInTheDocument();
});

test("a refused drift shows under the colorway row, and not in the status bar", async () => {
  const { screen, receive } = await renderWired(
    <>
      <StatusBar planNote={null} />
      <LookPanel />
    </>,
  );
  receive(refused("drift", "the looks file is read-only"));
  await expect.element(screen.getByRole("alert")).toHaveTextContent("the looks file is read-only");
  expect(document.querySelector(".status-bar")?.textContent).toBe("");
});

test("the chips are one tab stop, the pressed one, and the arrow keys, Home and End move between them", async () => {
  const names = ["green", "red", "blue", "gold"];
  const { screen, receive } = await renderWired(<LookPanel />);
  receive(stack({ colorways: names, colorway: "red" }));
  const chips = screen.getByRole("toolbar", { name: "colorways" });
  const buttons = [...chips.element().querySelectorAll("button")];
  expect(buttons.map((b) => b.tabIndex)).toEqual([-1, 0, -1, -1]);
  buttons[1]!.focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(document.activeElement).toBe(buttons[2]);
  await userEvent.keyboard("{End}");
  expect(document.activeElement).toBe(buttons[3]);
  await userEvent.keyboard("{ArrowRight}");
  expect(document.activeElement).toBe(buttons[0]);
  await userEvent.keyboard("{ArrowLeft}");
  expect(document.activeElement).toBe(buttons[3]);
  await userEvent.keyboard("{Home}");
  expect(document.activeElement).toBe(buttons[0]);
  // With none pressed, the first takes Tab.
  receive(stack({ colorways: names, colorway: null }));
  expect([...chips.element().querySelectorAll("button")].map((b) => b.tabIndex)).toEqual([0, -1, -1, -1]);
});

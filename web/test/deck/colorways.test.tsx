import { expect, test } from "vitest";
import type { AuraState } from "../../src/aura/aura";
import { LookPanel } from "../../src/deck/LookPanel";
import { AURA } from "../fixtures/messages";
import { renderWired } from "../harness";

const stack = (patch: Partial<AuraState["stack"]>) => ({ type: "aura" as const, ...AURA, stack: { ...AURA.stack, ...patch } });

test("the look's colorways are chips above its knobs, the active one pressed, and a press sends the colorway", async () => {
  const { screen, sent, receive } = await renderWired(<LookPanel />);
  const chips = screen.getByRole("group", { name: "colorways" });
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
  const chips = screen.getByRole("group", { name: "colorways" });
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
  await expect.element(screen.getByRole("group", { name: "colorways" })).not.toBeInTheDocument();
});

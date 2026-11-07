import { act } from "react";
import { expect, test } from "vitest";
import { page } from "vitest/browser";
import { App } from "../../src/app/App";
import { AURA } from "../fixtures/messages";
import { renderWired } from "./harness";

/** The style rules inside `@media (pointer: coarse)`, and, unless `only`, inside a query that adds to it. */
function coarseRules(only = false): CSSStyleRule[] {
  const sheets = [...document.styleSheets].flatMap((sheet) => [...sheet.cssRules]);
  return sheets
    .filter((r): r is CSSMediaRule => r instanceof CSSMediaRule && (only ? r.conditionText === "(pointer: coarse)" : r.conditionText.includes("pointer: coarse")))
    .flatMap((m) => [...m.cssRules])
    .filter((r): r is CSSStyleRule => r instanceof CSSStyleRule);
}

test("the document never scrolls under the frame, with a palette's hidden inputs far down the slot", async () => {
  await renderWired(<App />);
  await expect.poll(() => document.querySelector(".color-control input")).not.toBeNull();
  const slot = document.querySelector<HTMLElement>(".slot")!;
  expect(slot.scrollHeight).toBeGreaterThan(slot.clientHeight); // the palette is below the fold
  expect(document.scrollingElement!.scrollHeight).toBe(innerHeight);
});

test("on touch, every slider and color strip moves by its thumb alone, so a swipe on its track scrolls", async () => {
  await renderWired(<App />);
  const rules = coarseRules();
  const off = (el: Element) => rules.some((r) => r.style.pointerEvents === "none" && el.matches(r.selectorText));
  const param = document.querySelector('.param [data-scope="slider"][data-part="control"]')!;
  const strip = document.querySelector('.color-part [data-scope="slider"][data-part="control"]')!;
  const master = document.querySelector('.master [data-part="control"]')!;
  expect([off(param), off(strip), off(master)]).toEqual([true, true, true]);
});

test("on touch on a narrow phone, a tap at the centre of a knob's − is the −, never its reset, and nothing scrolls sideways", async () => {
  await page.viewport(320, 700);
  const touch = document.createElement("style");
  touch.textContent = coarseRules().map((r) => r.cssText).join("\n");
  document.head.append(touch);
  try {
    const { store } = await renderWired(<App />);
    await expect.poll(() => document.querySelectorAll(".param .number-entry").length).toBeGreaterThan(1);
    act(() => store.receive({ type: "params", values: Object.fromEntries(store.getState().params.map((p) => [p.name, p.kind === "float" ? p.hi : p.default])) }));
    const minus = [...document.querySelectorAll<HTMLElement>('.param [data-part="decrement-trigger"]')].filter((el) => el.checkVisibility());
    expect(minus.length).toBeGreaterThan(1);
    const hit = minus.map((el) => {
      el.scrollIntoView({ block: "center" });
      const r = el.getBoundingClientRect();
      return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === el;
    });
    expect(hit.every(Boolean)).toBe(true);
    const slot = document.querySelector<HTMLElement>(".slot")!; // a color strip's thumb at its top stays in the column
    expect(slot.scrollWidth).toBeLessThanOrEqual(slot.clientWidth);
  } finally {
    touch.remove();
    await page.viewport(414, 896);
  }
});

test("a lost connection's banner lies over the stage: nothing under it moves", async () => {
  const { screen, store } = await renderWired(<App />);
  const top = () => document.querySelector(".stage-area")!.getBoundingClientRect().top;
  const before = top();
  act(() => store.disconnected());
  await expect.element(screen.getByText(/Lost pewpew/)).toBeVisible();
  expect(top()).toBe(before);
});

test("every group on the page has a name", async () => {
  const { screen } = await renderWired(<App />);
  await screen.getByRole("button", { name: "look settings" }).click();
  await expect.poll(() => document.querySelectorAll(".param").length).toBeGreaterThan(3);
  const unnamed = [...document.querySelectorAll<HTMLElement>('[role="group"]')]
    .filter((el) => el.checkVisibility() && !el.closest('[aria-hidden="true"]'))
    .filter((el) => !el.getAttribute("aria-label") && !el.getAttribute("aria-labelledby"))
    .map((el) => el.className || `${el.dataset.scope}/${el.dataset.part}`);
  expect(unnamed).toEqual([]);
});

test("on a wide touch screen blackout has a row of its own under the brightness's, at its end: the slider comes straight after ☀", async () => {
  await page.viewport(1024, 768);
  const touch = document.createElement("style");
  touch.textContent = coarseRules(true).map((r) => r.cssText).join("\n"); // a tablet, not a phone on its side
  document.head.append(touch);
  try {
    const { screen, receive } = await renderWired(<App />);
    receive({ type: "aura", ...AURA, cap: 0.8 }); // a max, with its ?
    const blackout = screen.getByRole("button", { name: "blackout" });
    await expect.element(blackout).toBeVisible();
    const [sun, slider, steps, row] = [".master-label", ".master [data-part=control]", ".master .joined", ".master"].map((sel) => document.querySelector(sel)!.getBoundingClientRect());
    const b = blackout.element().getBoundingClientRect();
    // The slider takes all the room between ☀ and the steps.
    expect(slider!.left - sun!.right).toBeLessThanOrEqual(16);
    expect(steps!.left - slider!.right).toBeGreaterThanOrEqual(0);
    expect(steps!.left - slider!.right).toBeLessThanOrEqual(16);
    expect(b.top).toBeGreaterThanOrEqual(steps!.bottom);
    expect(Math.round(b.right)).toBe(Math.round(row!.right));
    await screen.getByRole("button", { name: "about max" }).click();
    const note = document.querySelector(".master > .disclosure-note")!.getBoundingClientRect();
    expect(note.top).toBeGreaterThanOrEqual(b.bottom);
  } finally {
    touch.remove();
    await page.viewport(414, 896);
  }
});

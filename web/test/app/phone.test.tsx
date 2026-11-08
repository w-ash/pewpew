import { expect, test } from "vitest";
import { page } from "vitest/browser";
import { App } from "../../src/app/App";
import { renderWired } from "../harness";

/** The style rules inside `@media (pointer: coarse)`, applied as plain rules: a test page's pointer is fine. */
function touchRules(): string {
  return [...document.styleSheets]
    .flatMap((sheet) => [...sheet.cssRules])
    .filter((r): r is CSSMediaRule => r instanceof CSSMediaRule && r.conditionText.includes("pointer: coarse"))
    .flatMap((m) => [...m.cssRules])
    .map((r) => r.cssText)
    .join("\n");
}

const visible = (el: Element) => (el as HTMLElement).checkVisibility();

/** The label of an element, for a failure message. */
const name = (el: Element) => `${el.tagName.toLowerCase()}.${el.className || ""} "${(el.getAttribute("aria-label") ?? el.textContent ?? "").trim().slice(0, 30)}"`;

/** A control under a finger is drawn smaller and answers on a ::before that reaches past its edges
 * (web/src/design/controls.css), so its target is the larger of the two. */
function target(el: Element): number {
  return Math.max(el.getBoundingClientRect().height, Number.parseFloat(getComputedStyle(el, "::before").height) || 0);
}

/** The Console at 390 x 844 under a finger, with the look's settings open; `check` reads the page. */
async function onPhone(check: () => void) {
  await page.viewport(390, 844);
  const touch = document.createElement("style");
  touch.textContent = touchRules();
  document.head.append(touch);
  try {
    const { screen } = await renderWired(<App />);
    await expect.poll(() => document.querySelectorAll(".param").length).toBeGreaterThan(1);
    await screen.getByRole("button", { name: "look settings" }).click();
    check();
  } finally {
    touch.remove();
    await page.viewport(414, 896);
  }
}

const smallControls = () =>
  [...document.querySelectorAll("button, [role=tab]")]
    .filter(visible)
    .filter((el) => target(el) < 44)
    .map((el) => `${name(el)} ${target(el)}`);

test("on a phone, the Console's controls are at least 44 px and its fields 16 px, so iOS does not zoom", async () => {
  await onPhone(() => {
    const controls = [...document.querySelectorAll("button, [role=tab]")].filter(visible);
    expect(controls.length).toBeGreaterThan(5);
    expect(document.querySelectorAll(".stop-marker").length).toBeGreaterThan(0);
    expect(smallControls()).toEqual([]);
    const fields = [...document.querySelectorAll("input, select, textarea")].filter(visible);
    expect(fields.length).toBeGreaterThan(3);
    const tiny = fields.filter((el) => Number.parseFloat(getComputedStyle(el).fontSize) < 16).map((el) => `${name(el)} ${getComputedStyle(el).fontSize}`);
    expect(tiny).toEqual([]);
  });
});

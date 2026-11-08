import { expect, test } from "vitest";
import { userEvent } from "vitest/browser";
import { ParamField } from "../../src/params/ParamField";
import { StatusBar } from "../../src/status/StatusBar";
import { LookKnobs, LookSignals } from "../../src/params/ParamPanel";
import { SETTLE_MS } from "../../src/design/useDraft";
import { StepStatus } from "../../src/design/StepStatus";
import { decodeParam } from "../../src/params/kinds";
import type { Gradient, HSV, PaletteParam } from "../../src/params/schema";
import type { ClientMessage } from "../../src/wire/protocol";
import { param, record } from "../fixtures/describe";
import { first, GREETING, refused, AURA } from "../fixtures/messages";
import { Layers, pastDoubleTap, renderWired } from "../harness";

type SetMessage = Extract<ClientMessage, { type: "set" }>;
const sets = (sent: ClientMessage[]) => sent.filter((m): m is SetMessage => m.type === "set");

test("a float slider works from the keyboard and reads its value with the unit", async () => {
  const { screen, sent } = await renderWired(<ParamField p={param("metaballs", "speed")} />, "metaballs");
  const slider = screen.getByRole("slider");
  await expect.element(slider).toHaveAttribute("aria-valuetext", "0.100 Hz");
  await expect.element(slider).toHaveAccessibleName("speed");
  await expect.element(screen.getByText("Hz")).toBeVisible();
  slider.element().focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "speed", value: 0.105 });
  await expect.element(slider).toHaveAttribute("aria-valuetext", "0.105 Hz");
});

test("a render error just after a knob of the node that raised was set names the knob and offers its value back", async () => {
  const p = decodeParam({ ...record("zoo_test", "level"), name: "layers.base.zoo.level" });
  const { screen, sent, receive } = await renderWired(
    <>
      <StatusBar planNote={null} />
      <ParamField p={p} />
    </>,
  );
  await screen.getByRole("button", { name: "increase level" }).click();
  receive({ type: "params", values: { "layers.base.zoo.level": 0.505 } });
  await screen.getByRole("button", { name: "increase level" }).click();
  receive({ type: "status", error: "layers.base.zoo.render raised: boom", source: "render", path: "layers.base.zoo" });
  await expect.element(screen.getByText("The room is pulsing red: Zoo failed after level went to 0.510.")).toBeVisible();
  await screen.getByRole("button", { name: "put back 0.500" }).click(); // the value before the edit, not the step before
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "layers.base.zoo.level", value: 0.5 });
});

test("a knob's help shows under its line, by its ?, while the ? is open, and describes its control always", async () => {
  const { screen } = await renderWired(<ParamField p={param("noise", "speed")} />, "noise");
  const slider = screen.getByRole("slider", { name: "speed" });
  const help = screen.getByText("How fast the hills change");
  await expect.element(help).not.toBeVisible();
  await expect.element(slider).toHaveAccessibleDescription("How fast the hills change");
  await expect.element(screen.getByRole("spinbutton", { name: "speed" })).toHaveAccessibleDescription("How fast the hills change");
  const ask = screen.getByRole("button", { name: "about speed" });
  await ask.click();
  await expect.element(ask).toHaveAttribute("aria-expanded", "true");
  await expect.element(ask).toHaveAttribute("aria-controls", help.element().id);
  await expect.element(help).toBeVisible();
  const line = help.element().getBoundingClientRect();
  expect(line.top).toBeGreaterThanOrEqual(ask.element().getBoundingClientRect().bottom - 1);
  expect(line.bottom).toBeLessThanOrEqual(slider.element().getBoundingClientRect().top);
  await ask.click();
  await expect.element(help).not.toBeVisible();
});

test("from a value between steps, − and + step to the nearest step that way, not past it", async () => {
  const p = decodeParam({ ...record("zoo_test", "level"), lo: 0.5, hi: 5, step: 0.2, decimals: 1, default: 3 });
  const { screen, receive, sent } = await renderWired(<ParamField p={p} />);
  receive({ type: "params", values: { level: 3 } });
  await expect.element(screen.getByRole("spinbutton", { name: "level" })).toHaveValue("3.0");
  await screen.getByRole("button", { name: "decrease level" }).click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "level", value: 2.9 });
  receive({ type: "params", values: { level: 2.9 } });
  await screen.getByRole("button", { name: "increase level" }).click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "level", value: 3.1 });
  receive({ type: "params", values: { level: 3.1 } });
  await screen.getByRole("button", { name: "decrease level" }).click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "level", value: 2.9 });
});

test("− and + step once on a click no press came before, as assistive tech sends, and once on a real one", async () => {
  const p = decodeParam({ ...record("zoo_test", "level"), lo: 0, hi: 5, step: 0.5, decimals: 1, default: 1 });
  const { screen, receive, sent } = await renderWired(<ParamField p={p} />);
  receive({ type: "params", values: { level: 1 } });
  await expect.element(screen.getByRole("spinbutton", { name: "level" })).toHaveValue("1.0");
  (screen.getByRole("button", { name: "increase level" }).element() as HTMLElement).click();
  expect(sets(sent)).toEqual([{ type: "set", name: "level", value: 1.5 }]);
  receive({ type: "params", values: { level: 1.5 } });
  await expect.element(screen.getByRole("spinbutton", { name: "level" })).toHaveValue("1.5");
  await screen.getByRole("button", { name: "decrease level" }).click();
  expect(sets(sent).slice(1)).toEqual([{ type: "set", name: "level", value: 1 }]);
});

test("every entry of a panel ends at one edge, with a unit or without", async () => {
  await renderWired(<Layers />, "noise");
  const ends = [...document.querySelectorAll(".number-control .number-entry [data-part='control']")].map((el) => Math.round(el.getBoundingClientRect().right));
  expect(ends.length).toBeGreaterThan(1);
  expect(new Set(ends).size).toBe(1);
});

// Before each `fill` the engine's echo lands and the box shows it: Zag writes
// a new value into the box, and puts the caret back, an animation frame later,
// so a `fill` at once can lose its select-all to it. No person types that fast.
test("a typed value outside the range says what it became; garbage says it is not a number", async () => {
  const { screen, sent, receive } = await renderWired(<ParamField p={param("zoo_test", "level")} />);
  const box = screen.getByRole("spinbutton", { name: "level" });
  await box.fill("5");
  await userEvent.keyboard("{Enter}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "level", value: 1 });
  await expect.element(screen.getByRole("status")).toHaveTextContent("5 is outside 0.000…1.000: kept to 1.000");
  // The engine's echo: unechoed, the box falls back to the old value after SETTLE_MS (useDraft), and a
  // slow run steps from that.
  receive({ type: "params", values: { level: 1 } });
  await expect.element(box).toHaveValue("1.000");
  await screen.getByRole("button", { name: "decrease level" }).click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "level", value: 0.995 });
  await expect.element(screen.getByRole("status")).not.toBeInTheDocument();
  receive({ type: "params", values: { level: 0.995 } });
  await expect.element(box).toHaveValue("0.995");
  await box.fill("-");
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByRole("status")).toHaveTextContent("‘-’ is not a number");
});

test("a letter typed into an entry says it is not a number, and sends nothing", async () => {
  const { screen, sent } = await renderWired(<ParamField p={param("zoo_test", "level")} />);
  screen.getByRole("spinbutton", { name: "level" }).element().focus();
  await userEvent.keyboard("x");
  await expect.element(screen.getByRole("status")).toHaveTextContent("‘x’ is not a number");
  await userEvent.keyboard("{Enter}");
  expect(sets(sent)).toEqual([]);
});

test("Esc drops a typed number: the box shows the knob's value again, and leaving it sends nothing", async () => {
  const { screen, sent } = await renderWired(<ParamField p={param("zoo_test", "level")} />);
  const box = screen.getByRole("spinbutton", { name: "level" });
  const before = (box.element() as HTMLInputElement).value;
  box.element().focus();
  await userEvent.keyboard("{Control>}a{/Control}0.123");
  await userEvent.keyboard("{Escape}");
  await expect.element(box).toHaveValue(before);
  await userEvent.keyboard("{Tab}");
  expect(sets(sent)).toEqual([]);
});

test("a typed value between steps says which step it became; one on a step, or a hue past 360, says nothing", async () => {
  const { screen, sent, receive } = await renderWired(<ParamField p={param("zoo_test", "color")} />);
  const hue = screen.getByRole("spinbutton", { name: "color hue" });
  await hue.fill("201");
  await userEvent.keyboard("{Enter}");
  expect(sets(sent).at(-1)).toMatchObject({ value: { h: 202 } });
  await expect.element(screen.getByRole("status")).toHaveTextContent("201 is between steps of 2: kept to 202");
  receive({ type: "params", values: { color: { h: 202, s: 1, v: 1 } } });
  await expect.element(hue).toHaveValue("202");
  await hue.fill("370");
  await userEvent.keyboard("{Enter}");
  expect(sets(sent).at(-1)).toMatchObject({ value: { h: 10 } });
  await expect.element(screen.getByRole("status")).not.toBeInTheDocument();
});

test("each kind renders its own control", async () => {
  const { screen } = await renderWired(<Layers />);
  await expect.element(screen.getByRole("slider", { name: "level" })).toBeVisible();
  await expect.element(screen.getByRole("slider", { name: "bands" })).toHaveAttribute("aria-valuetext", "2");
  await expect.element(screen.getByRole("switch", { name: "invert" })).toBeVisible();
  await expect.element(screen.getByRole("radio", { name: "steps" })).toBeVisible();
  await expect.element(screen.getByRole("spinbutton", { name: "color hue" })).toHaveValue("120");
  await expect.element(screen.getByRole("spinbutton", { name: "color saturation" })).toHaveValue("100"); // a whole percent
  await expect.element(screen.getByRole("combobox", { name: "palette" })).toHaveValue("ember");
});

test("a choice of more than five options is a list, and Backspace on it resets", async () => {
  const keys = ["a", "b", "c", "d", "e", "f"];
  const many = { ...record("zoo_test", "shape"), default: "a", options: keys.map((k) => ({ value: k, label: k.toUpperCase() })) };
  const { screen, receive, sent } = await renderWired(<ParamField p={decodeParam(many)} />);
  const list = screen.getByRole("combobox", { name: "shape" });
  await list.selectOptions("d"); // options read in lower case
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "shape", value: "d" });
  receive({ type: "params", values: { shape: "d" } });
  list.element().focus();
  await userEvent.keyboard("{Backspace}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "shape", value: "a" });
});

test("an angle is a slider as every number knob is, with a compass that points where the param points", async () => {
  const { screen, receive } = await renderWired(<ParamField p={param("rotate", "angle")} />, "rotate");
  receive({ type: "params", values: { angle: 90 } });
  const slider = screen.getByRole("slider", { name: "angle" });
  await expect.element(slider).toHaveAttribute("aria-valuetext", "90°");
  const compass = document.querySelector<HTMLElement>(".compass")!;
  expect(compass.getAttribute("aria-hidden")).toBe("true");
  expect(compass.style.rotate).toBe("-90deg"); // counterclockwise from +x, as the room plan reads
  receive({ type: "params", values: { angle: 0 } });
  await expect.poll(() => compass.style.rotate).toBe("0deg");
});

test("a value with a text label reads it: sides of 0 reads round", async () => {
  const { screen } = await renderWired(<Layers />, "shape");
  await expect.element(screen.getByRole("slider", { name: "sides" })).toHaveAttribute("aria-valuetext", "round");
});

test("a drag holds its value against an echo, then follows the agreeing echo at once", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("zoo_test", "level")} />);
  const control = document.querySelector<HTMLElement>('[data-scope="slider"][data-part="control"]')!;
  const box = control.getBoundingClientRect();
  const at = (f: number) => ({ clientX: box.left + f * box.width, clientY: box.top + box.height / 2, pointerId: 1, bubbles: true });
  const slider = screen.getByRole("slider");
  control.dispatchEvent(new PointerEvent("pointerdown", { ...at(0.6), button: 0, buttons: 1 }));
  await expect.poll(() => Number(slider.element().getAttribute("aria-valuenow"))).toBeGreaterThan(0.55);
  document.dispatchEvent(new PointerEvent("pointermove", { ...at(0.9), buttons: 1 }));
  await expect.poll(() => Number(slider.element().getAttribute("aria-valuenow"))).toBeGreaterThan(0.85);
  const held = slider.element().getAttribute("aria-valuenow");
  receive({ type: "params", values: { level: 0.1 } });
  await expect.element(slider).toHaveAttribute("aria-valuenow", held!);
  document.dispatchEvent(new PointerEvent("pointerup", { ...at(0.9) }));
  expect(sets(sent).length).toBeGreaterThan(0);
  await expect.poll(() => slider.element().hasAttribute("data-dragging")).toBe(false);
  receive({ type: "params", values: { level: Number(held) } });
  receive({ type: "params", values: { level: 0.3 } });
  // Well inside SETTLE_MS: the draft cleared on the agreeing echo, not on the timer.
  await expect.element(slider, { timeout: SETTLE_MS / 4 }).toHaveAttribute("aria-valuenow", "0.3");
});

test("↺ sends the default as declared, even between steps", async () => {
  const p = decodeParam({ ...record("zoo_test", "level"), default: 0.333 });
  const { screen, receive, sent } = await renderWired(<ParamField p={p} />);
  receive({ type: "params", values: { level: 0.9 } });
  const dot = screen.getByRole("button", { name: "reset level to 0.333" });
  await dot.click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "level", value: 0.333 });
  receive({ type: "params", values: { level: 0.333 } });
  await expect.element(dot).not.toBeInTheDocument();
});

test("an edit of one color part snaps that part and sends the others as they were", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("zoo_test", "color")} />);
  let at = { h: 123.4, s: 0.5555, v: 0.777 };
  const echo = async (next: HSV) => {
    at = next;
    receive({ type: "params", values: { color: at } });
    await expect.element(hue).toHaveValue(String(Math.round(at.h)));
  };
  const hue = screen.getByRole("spinbutton", { name: "color hue" });
  await echo(at);
  screen.getByRole("slider", { name: "color saturation" }).element().focus();
  await userEvent.keyboard("{ArrowUp}");
  expect(sets(sent).at(-1)?.value).toEqual({ ...at, s: 0.56 });
  await echo({ ...at, s: 0.56 });
  await hue.fill("400");
  await userEvent.keyboard("{Enter}");
  expect(sets(sent).at(-1)?.value).toEqual({ ...at, h: 40 });
  await echo({ ...at, h: 40 });
  const strip = document.querySelector<HTMLElement>('[data-channel="h"] [data-part="control"]')!;
  const box = strip.getBoundingClientRect();
  const point = { clientX: box.left + box.width / 2, clientY: box.top + box.height / 2, pointerId: 1, bubbles: true };
  strip.dispatchEvent(new PointerEvent("pointerdown", { ...point, button: 0, buttons: 1 }));
  document.dispatchEvent(new PointerEvent("pointerup", point));
  await expect.poll(() => (sets(sent).at(-1)!.value as HSV).h).not.toBe(40);
  const dragged = sets(sent).at(-1)?.value as HSV;
  expect([dragged.h % 2, dragged.s, dragged.v]).toEqual([0, at.s, at.v]);
});

test("reset by ↺", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("zoo_test", "bands")} />);
  const dot = screen.getByRole("button", { name: "reset bands to 2" });
  expect(dot.query()).toBeNull();
  receive({ type: "params", values: { bands: 5 } });
  await expect.element(dot).toBeVisible();
  await dot.click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "bands", value: 2 });
});

test("a knob off the saved look shows ↺ at rest, its sign of changed, and ↺ puts the saved value back, never past it", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("zoo_test", "bands")} />);
  receive({ type: "aura", ...AURA, looks: { ...AURA.looks!, saved: { bands: 4 } } });
  receive({ type: "params", values: { bands: 4 } });
  const reset = () => document.querySelector<HTMLButtonElement>(".reset")!;
  await expect.poll(() => reset().hidden).toBe(true); // at the saved value: nothing to put back
  receive({ type: "params", values: { bands: 5 } });
  await expect.poll(() => reset().hidden).toBe(false);
  expect(reset().hasAttribute("data-changed")).toBe(true);
  expect(getComputedStyle(reset()).opacity).toBe("1"); // shown at rest, not only under a pointer
  await screen.getByRole("button", { name: "revert bands to 4" }).click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "bands", value: 4 });
  receive({ type: "params", values: { bands: 4 } });
  await expect.poll(() => reset().hidden).toBe(true); // back at the saved value: no second press goes to the default
});

test("reset by Backspace on the control, not in a text box", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("zoo_test", "level")} />);
  receive({ type: "params", values: { level: 0.9 } });
  // A click, not focus(): a Backspace that reaches the page makes WebKit go back.
  const box = screen.getByRole("spinbutton");
  await box.click();
  await expect.element(box).toHaveFocus();
  await userEvent.keyboard("{Backspace}");
  expect(sets(sent)).toEqual([]);
  screen.getByRole("slider").element().focus();
  await userEvent.keyboard("{Backspace}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "level", value: 0.5 });
});

test("reset by Backspace on a switch", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("zoo_test", "invert")} />);
  receive({ type: "params", values: { invert: true } });
  const box = screen.getByRole("switch", { name: "invert" });
  box.element().focus();
  await expect.element(box).toHaveFocus();
  sent.length = 0;
  await userEvent.keyboard("{Backspace}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "invert", value: false });
});

test("a periodic value steps round its end", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("rotate", "angle")} />, "rotate");
  receive({ type: "params", values: { angle: 360 } });
  await screen.getByRole("button", { name: "increase angle" }).click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "angle", value: 2 });
  screen.getByRole("spinbutton", { name: "angle" }).element().focus();
  await userEvent.keyboard("{Home}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "angle", value: 0 });
});

test("a step key after typing steps from the typed value and shows the result", async () => {
  const { screen, sent } = await renderWired(<ParamField p={param("zoo_test", "bands")} />);
  const box = screen.getByRole("spinbutton", { name: "bands" });
  await box.fill("5");
  await userEvent.keyboard("{ArrowUp}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "bands", value: 6 });
  await expect.element(box).toHaveValue("6");
});

test("a refusal stops showing once another tab moves the value", async () => {
  const { screen, receive } = await renderWired(<ParamField p={param("zoo_test", "level")} />);
  receive(refused("set", "no, not that", "level"));
  await expect.element(screen.getByText("no, not that")).toBeVisible();
  receive({ type: "params", values: { level: 0.3 } });
  await expect.element(screen.getByText("no, not that")).not.toBeInTheDocument();
});

test("typed entry sends on Enter, and ± steps send at once", async () => {
  const { screen, sent } = await renderWired(<ParamField p={param("zoo_test", "bands")} />);
  const box = screen.getByRole("spinbutton", { name: "bands" });
  await box.fill("4");
  expect(sets(sent)).toEqual([]);
  await userEvent.keyboard("{Enter}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: "bands", value: 4 });
  await screen.getByRole("button", { name: "increase bands" }).click();
  expect(sets(sent).at(-1)?.type).toBe("set");
});

test("a refused set shows its reason and the control snaps back", async () => {
  const { screen, receive } = await renderWired(<ParamField p={param("zoo_test", "level")} />);
  screen.getByRole("slider").element().focus();
  await userEvent.keyboard("{End}");
  await expect.element(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "1");
  receive(refused("set", "level must be within 0.0..0.5, got 1.0", "level"));
  await expect.element(screen.getByText("level must be within 0.0..0.5, got 1.0")).toBeVisible();
  await expect.element(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "0.5");
});

test("groups follow the ungrouped params and fold, remembered on this device", async () => {
  const { screen } = await renderWired(<Layers />);
  const group = screen.getByRole("button", { name: "shape", exact: true });
  await expect.element(group).toHaveAttribute("aria-expanded", "true");
  await group.click();
  await expect.element(group).toHaveAttribute("aria-expanded", "false");
  expect(localStorage.getItem("pewpew.closed-groups")).toBe('["Shape"]');
  localStorage.clear();
});

test("defaults takes two presses", async () => {
  const { screen, receive, sent } = await renderWired(<Layers />);
  receive({ type: "params", values: { bands: 5 } });
  await screen.getByRole("button", { name: "reset to defaults" }).click();
  expect(sets(sent)).toEqual([]);
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to reset all" }).click();
  expect(sets(sent).map((m) => m.name)).toEqual(["level", "bands", "invert", "shape", "color", "palette"]);
});

test("the hue strip's keys step by the hue's own step, and wrap past 360°", async () => {
  const { screen, receive, sent } = await renderWired(<ParamField p={param("zoo_test", "color")} />);
  receive({ type: "params", values: { color: { h: 350, s: 1, v: 1 } } });
  screen.getByRole("slider", { name: "color hue" }).element().focus();
  const hues: number[] = [];
  const hue = screen.getByRole("slider", { name: "color hue" });
  for (const key of ["{PageUp}", "{ArrowDown}", "{ArrowUp}", "{ArrowUp}", "{PageDown}", "{Shift>}{ArrowRight}{/Shift}"]) {
    await userEvent.keyboard(key);
    const sent_ = sets(sent).at(-1)!.value as HSV;
    hues.push(sent_.h);
    // The engine's echo: unechoed, the next key steps from the old value once SETTLE_MS passes (useDraft).
    receive({ type: "params", values: { color: sent_ } });
    await expect.element(hue).toHaveAttribute("aria-valuenow", String(sent_.h));
  }
  expect(hues).toEqual([10, 8, 10, 12, 352, 12]);
});

const PALETTE = param("zoo_test", "palette") as PaletteParam;
const palettes = (sent: ClientMessage[]) => sets(sent).map((m) => m.value as Gradient);

test("a palette picks a preset, and shows custom once a stop is edited", async () => {
  const { screen, sent, receive } = await renderWired(<ParamField p={PALETTE} />);
  const presets = screen.getByRole("combobox", { name: "palette" });
  await expect.element(presets).toHaveValue("ember");
  await presets.selectOptions("ocean");
  expect(palettes(sent).at(-1)).toEqual(PALETTE.presets[1]!.value);
  receive({ type: "params", values: { palette: PALETTE.presets[1]!.value } });
  await expect.element(presets).toHaveValue("ocean");
  await screen.getByRole("button", { name: /^stop 1 at/ }).click();
  await screen.getByRole("spinbutton", { name: "stop 1 hue" }).fill("100");
  await userEvent.keyboard("{Enter}");
  const edited = palettes(sent).at(-1)!;
  expect(edited.label).toBe("");
  expect(edited.stops.map((x) => x.h)).toEqual([100, 210, 190, 175]);
  receive({ type: "params", values: { palette: edited } });
  await expect.element(presets).toHaveValue("");
  await expect.element(screen.getByRole("option", { name: "custom" })).toBeInTheDocument();
});

test("a palette's markers open the stop to edit, and fold it again; the ends stay at 0 and 1", async () => {
  const { screen, sent } = await renderWired(<ParamField p={PALETTE} />);
  await expect.element(screen.getByRole("button", { name: "add stop" })).not.toBeInTheDocument(); // no stop editor until one is picked
  await screen.getByRole("button", { name: "stop 1 at 0.000" }).click();
  await expect.element(screen.getByText("starts the gradient, at 0")).toBeVisible();
  await screen.getByRole("button", { name: "stop 2 at 0.350" }).click();
  await expect.element(screen.getByRole("button", { name: "stop 2 at 0.350" })).toHaveAttribute("aria-pressed", "true");
  const position = screen.getByRole("spinbutton", { name: "stop 2 position" });
  await expect.element(position).toHaveValue("0.350");
  await position.fill("0.9");
  await userEvent.keyboard("{Enter}");
  expect(palettes(sent).at(-1)!.stops.map((x) => x.at)).toEqual([0, 0.7, 0.7, 1]); // stops at the next stop
  await screen.getByRole("button", { name: "stop 4 at 1.000" }).click();
  await expect.element(screen.getByText("ends the gradient, at 1")).toBeVisible();
  await expect.element(screen.getByRole("spinbutton", { name: "stop 4 position" })).not.toBeInTheDocument();
  await screen.getByRole("button", { name: "stop 4 at 1.000" }).click();
  await expect.element(screen.getByText("ends the gradient, at 1")).not.toBeInTheDocument();
});

test("a palette adds a stop halfway to the next, and keeps at least two", async () => {
  const { screen, sent, receive } = await renderWired(<ParamField p={PALETTE} />);
  await screen.getByRole("button", { name: "stop 1 at 0.000" }).click();
  await screen.getByRole("button", { name: "add stop" }).click();
  const added = palettes(sent).at(-1)!;
  expect(added.stops.map((x) => x.at)).toEqual([0, 0.175, 0.35, 0.7, 1]);
  expect(added.stops[1]).toMatchObject({ h: 0, s: 1, v: 0 }); // a copy of the stop it follows
  receive({ type: "params", values: { palette: added } });
  await expect.element(screen.getByRole("status").filter({ hasText: "stop 2 of 5" })).toBeVisible(); // said as it changes
  for (let n = 5; n > 2; n--) {
    await screen.getByRole("button", { name: "remove stop" }).click(); // two presses: a third cannot cascade
    expect(palettes(sent)).toHaveLength(6 - n);
    pastDoubleTap();
    await screen.getByRole("button", { name: "again to remove" }).click();
    receive({ type: "params", values: { palette: palettes(sent).at(-1)! } });
    await expect.element(screen.getByText(`of ${n - 1}`, { exact: false })).toBeVisible();
  }
  expect(palettes(sent).at(-1)!.stops.map((x) => x.at)).toEqual([0, 1]);
  const remove = screen.getByRole("button", { name: "remove stop" });
  await expect.element(remove).toHaveAttribute("aria-disabled", "true");
  (remove.element() as HTMLElement).click(); // off, but it says why when pressed
  await expect.element(screen.getByText("a palette needs two stops")).toBeVisible();
  expect(palettes(sent)).toHaveLength(4);
});

test("a palette's strip draws the gradient as the LEDs show it", async () => {
  const { screen } = await renderWired(<ParamField p={PALETTE} />);
  const strip = document.querySelector<HTMLElement>(".palette-strip")!;
  expect(strip.style.backgroundImage).toContain("oklab");
  expect(getComputedStyle(strip).backgroundImage).toContain("gradient");
  const end = screen.getByRole("button", { name: "stop 4 at 1.000" }).element() as HTMLElement;
  expect(end.style.color).toBe("rgb(255, 229, 148)"); // ember's last stop, (42°, 0.7, 1) at gamma 2.2
});

test("the main knobs are the look's own block, each also in its own place; a lone layer's are under its heading", async () => {
  const { screen, receive } = await renderWired(
    <>
      <LookKnobs />
      <Layers />
      <LookSignals />
    </>,
  );
  for (const msg of GREETING) receive(msg);
  // The greeting's look lists the macro and the level in front: the macro, a knob of the look's own, is called by its name and
  // says what it drives; with one layer, the level says nothing more.
  await expect.element(screen.getByRole("slider", { name: "macro", exact: true })).toBeVisible();
  await expect.element(screen.getByRole("slider", { name: "macro", exact: true })).toHaveAccessibleDescription(/^→ color/);
  expect(screen.getByRole("slider", { name: "level", exact: true }).elements()).toHaveLength(2); // a main knob, and in its place
  await expect.element(screen.getByRole("heading", { name: "base · 1 step" })).toBeVisible();
  await expect.element(screen.getByRole("slider", { name: "bands" })).toBeVisible();
  // After the layers, the modulators, with a ? that says what one is: the sections start folded, each titled by its name,
  // then its kind and what it moves. The macro, in front by its name, is not one of them.
  await expect.element(screen.getByRole("heading", { name: "modulators" })).toBeVisible();
  const about = screen.getByRole("button", { name: "about modulators" });
  // By its key: the "?" lies on the frame's foot, where WebKit's harness sends a press but no click.
  about.element().focus();
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByText("A modulator keeps a knob moving: a wave, the beat, the music")).toBeVisible();
  await expect.element(about).toHaveAttribute("aria-expanded", "true");
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByRole("button", { name: "breath · LFO → level" })).toHaveAttribute("aria-expanded", "false");
  await expect.element(screen.getByRole("button", { name: /^macro · macro/ })).not.toBeInTheDocument();
  const records = first("declare").params as Record<string, unknown>[];
  const top = records.flatMap((r) => (String(r.name).startsWith("layers.base.")
    ? [{ ...r, name: String(r.name).replace("layers.base.", "layers.top."), layer: "top" }] : []));
  receive({ type: "declare", params: [...records, ...top] });
  receive({ type: "aura", ...AURA, stack: { ...AURA.stack, layers: [...AURA.stack.layers, { id: "top", nodes: AURA.stack.layers[0]!.nodes }] } });
  await expect.element(screen.getByRole("heading", { name: "base · 1 step" })).not.toBeInTheDocument(); // each layer's are in its row
  await expect.element(screen.getByRole("heading", { name: "layers · top first" })).toBeVisible();
  await expect.element(screen.getByRole("slider", { name: "level · base" })).toBeVisible(); // with two layers, a main knob names its owner
  await expect.element(screen.getByRole("slider", { name: "opacity" })).not.toBeInTheDocument(); // in the layer's row
  localStorage.clear();
});

test("a knob a route moves shows where it is now, as a mark and a readout, while the thumb stays on its value", async () => {
  const { screen, receive } = await renderWired(
    <>
      <LookKnobs />
      <Layers />
    </>,
  );
  receive({ type: "aura", ...AURA, stack: { ...AURA.stack, routes: [{ source: "breath", path: "level", depth: -0.2 }], front: ["bands"] } });
  receive({ type: "mod", values: { level: 0.7 } });
  const level = screen.getByRole("slider", { name: "level" });
  await expect.element(level).toHaveAttribute("aria-valuetext", "0.500");
  // At rest the mark alone says a route moves it; the "?" says what, and where it is now.
  const moved = screen.getByText(/^modulated by ‘breath’ ±0\.2/);
  await expect.element(moved).not.toBeVisible();
  await expect.element(level).toHaveAccessibleDescription(/^modulated by ‘breath’ ±0\.2/); // an LFO swings both ways
  await screen.getByRole("button", { name: "about level" }).click();
  await expect.element(moved).toBeVisible();
  const readout = screen.getByText("· now 0.700");
  await expect.element(readout).toBeVisible();
  await expect.element(readout).toHaveAttribute("aria-hidden", "true");
  expect(document.querySelector(".live-mark")?.getAttribute("data-value")).toBe("0.7");
  const labels = [...document.querySelectorAll('[data-scope="field"][data-part="label"]')].map((l) => l.textContent);
  expect(labels.slice(0, 2)).toEqual(["bands", "level"]); // the front knob first, in lower case as shown
  receive({ type: "mod", values: {} });
  await expect.element(readout).not.toBeInTheDocument();
  expect(document.querySelector(".live-mark")).toBeNull();
  localStorage.clear();
});

test("a knob's pin makes it a main knob in one press, takes it off in two, and says so", async () => {
  const { screen, sent, receive } = await renderWired(
    <>
      <LookKnobs />
      <Layers />
      <StepStatus />
    </>,
  );
  for (const msg of GREETING) receive(msg);
  receive({ type: "aura", ...AURA, stack: { ...AURA.stack, front: ["layers.base.zoo.level"] } });
  const bands = screen.getByRole("button", { name: "bands in the main knobs" });
  await expect.element(bands).toHaveAttribute("aria-pressed", "false");
  await bands.click();
  expect(sent.at(-1)).toEqual({ type: "front", paths: ["layers.base.zoo.level", "layers.base.zoo.bands"] });
  await expect.poll(() => document.querySelector(".sr-only[role=status]")?.textContent).toBe("bands added to the main knobs");
  const level = screen.getByRole("button", { name: "level in the main knobs" });
  await expect.element(level.first()).toHaveAttribute("aria-pressed", "true");
  await level.first().click();
  expect(sent).toHaveLength(1); // armed: nothing taken off yet
  pastDoubleTap();
  await level.first().click();
  expect(sent.at(-1)).toEqual({ type: "front", paths: [] });
  // Focus goes to its copy in its own section, which stays.
  await expect.element(level.last()).toHaveFocus();
  localStorage.clear();
});

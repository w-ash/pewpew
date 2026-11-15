// The page's undo and redo of look edits: the history itself, on a store that heard the golden greeting,
// then its buttons and keys in the look's header.
import { expect, test } from "vitest";
import { userEvent } from "vitest/browser";
import type { AuraState } from "../../src/aura/aura";
import { LookPanel } from "../../src/deck/LookPanel";
import { useShortcutList } from "../../src/design/shortcuts";
import { StepStatus } from "../../src/design/StepStatus";
import { LayoutProvider, useLayoutMode } from "../../src/layout/LayoutMode";
import { SETTLE_MS } from "../../src/design/useDraft";
import { EditHistory, GROUP_MS } from "../../src/params/history";
import type { ClientMessage, Sender, ServerMessage } from "../../src/wire/protocol";
import { WireStore } from "../../src/wire/store";
import { AURA, first, GREETING } from "../fixtures/messages";
import { renderWired } from "../harness";

const LEVEL = "layers.base.zoo.level";
const BANDS = "layers.base.zoo.bands";
const MACRO = "signals.macro.value";
const PALETTE = "layers.base.zoo.palette";

type SetMessage = Extract<ClientMessage, { type: "set" }>;
const sets = (sent: readonly ClientMessage[]) => sent.filter((m): m is SetMessage => m.type === "set");
const values = (patch: Record<string, unknown>): ServerMessage => ({ type: "params", values: patch });
const aura = (patch: Partial<AuraState>, stack: Partial<AuraState["stack"]> = {}): ServerMessage => ({
  type: "aura", ...AURA, ...patch, stack: { ...AURA.stack, ...stack },
});

/** A history on a store that heard the greeting, its clock, and what it sent. Each set the page sends is
 * echoed, as the engine would, unless `echo` is false. */
function setup() {
  const store = new WireStore();
  for (const msg of GREETING) store.receive(msg);
  const sent: ClientMessage[] = [];
  const raw: Sender = { send: (m) => sent.push(m), sendLatest: (m) => sent.push(m), ask: async (m) => (sent.push(m), true) };
  let now = 0;
  const edits = new EditHistory(store, raw, () => now);
  const set = (name: string, value: unknown, echo = true) => {
    edits.sender.sendLatest({ type: "set", name, value });
    if (echo) store.receive(values({ [name]: value }));
  };
  const later = (ms: number) => {
    now += ms;
  };
  /** Wait out the task: sets after it are not one burst. */
  const nextTask = () => new Promise((r) => setTimeout(r, 0));
  /** A press of − or + or a step key: its set and its let go in one task, then the task ends. */
  const press = async (name: string, value: unknown, echo = true) => {
    set(name, value, echo);
    edits.seal(name);
    await nextTask();
  };
  /** A drag: its sets, each in a task of its own, then its let go in a later one. */
  const drag = async (name: string, ...path: unknown[]) => {
    for (const v of path) {
      set(name, v);
      await nextTask();
    }
    edits.seal(name);
    await nextTask();
  };
  return { store, sent, edits, set, later, nextTask, press, drag };
}

test("sets of one knob a moment apart are one step, from the value the engine had when it began", async () => {
  const { sent, edits, set, later, nextTask } = setup();
  for (const v of [0.6, 0.7, 0.75]) {
    set(LEVEL, v);
    later(GROUP_MS / 2);
    await nextTask();
  }
  edits.undo();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
  expect(edits.can(true)).toBe(false);
  edits.redo();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.75 });
});

test("a let go, a pause, or another knob starts a new step", async () => {
  const { sent, edits, set, later, nextTask, drag } = setup();
  await drag(LEVEL, 0.55, 0.6); // its control let go
  set(LEVEL, 0.7);
  later(GROUP_MS);
  await nextTask();
  set(LEVEL, 0.8);
  await nextTask();
  set(MACRO, 0.9);
  const undone = () => {
    edits.undo();
    return sets(sent).at(-1)!.value;
  };
  expect([undone(), undone(), undone(), undone()]).toEqual([0.5, 0.7, 0.6, 0.5]);
  expect(edits.can(true)).toBe(false);
});

test("the sets sent in one go, as reset to defaults sends them, are one step", async () => {
  const { sent, edits, set, nextTask } = setup();
  set(LEVEL, 0.9);
  edits.seal(LEVEL);
  await nextTask();
  set(LEVEL, 0.5);
  set(BANDS, 4);
  set(MACRO, 0.1);
  await nextTask();
  const said = edits.undo();
  expect(sets(sent).slice(-3)).toEqual([
    { type: "set", name: LEVEL, value: 0.9 },
    { type: "set", name: BANDS, value: 2 },
    { type: "set", name: MACRO, value: 0.5 },
  ]);
  expect(said).toBe("undid 3 knobs");
});

test("a step that ends where it began is not kept", async () => {
  const { edits, set, nextTask, press } = setup();
  set(LEVEL, 0.7);
  await nextTask();
  set(LEVEL, 0.5); // a drag the browser took, put back
  await nextTask();
  edits.seal(LEVEL);
  expect(edits.can(true)).toBe(false);
  await press(LEVEL, 0.505);
  await press(LEVEL, 0.5); // presses there and back
  expect(edits.can(true)).toBe(false);
  expect(edits.undo()).toBeNull();
});

test("presses of one knob less than GROUP_MS apart are one step; a drag, or a press after a pause, is a step of its own", async () => {
  const { sent, edits, later, press, drag } = setup();
  for (const v of [0.505, 0.51, 0.515, 0.52, 0.525]) {
    await press(LEVEL, v);
    later(GROUP_MS / 2);
  }
  await drag(LEVEL, 0.6, 0.7);
  await drag(LEVEL, 0.8);
  later(GROUP_MS);
  await press(LEVEL, 0.805);
  later(GROUP_MS);
  await press(LEVEL, 0.81);
  const undone: unknown[] = [];
  while (edits.undo()) undone.push(sets(sent).at(-1)!.value);
  expect(undone).toEqual([0.805, 0.8, 0.7, 0.525, 0.5]);
});

test("a step begins at the value this page sent last, while the engine's echo of it is on the way", async () => {
  const { sent, edits, later, drag, set, nextTask } = setup();
  await drag(LEVEL); // nothing yet
  set(LEVEL, 0.6, false);
  await nextTask();
  edits.seal(LEVEL);
  await nextTask();
  set(LEVEL, 0.7, false);
  await nextTask();
  edits.seal(LEVEL);
  const said = edits.undo();
  expect(said).toBe("undid level · zoo, back to 0.600");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.6 });
  edits.undo();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
  // Once the echo is late past SETTLE_MS, the engine's value is the knob's again.
  later(SETTLE_MS);
  set(LEVEL, 0.9, false);
  await nextTask();
  edits.seal(LEVEL);
  edits.undo();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
});

test("undo and redo leave a knob changed since this page set it, and drop its step", async () => {
  const { store, sent, edits, later, drag } = setup();
  await drag(LEVEL, 0.6);
  later(SETTLE_MS);
  store.receive(values({ [LEVEL]: 0.9 })); // another page
  const count = sets(sent).length;
  expect(edits.undo()).toBe("level · zoo was changed elsewhere: not undone");
  expect(sets(sent)).toHaveLength(count);
  expect([edits.can(true), edits.can(false)]).toEqual([false, false]);
  // In a step of two knobs, the other is undone; redo too skips a knob changed since.
  await drag(LEVEL, 0.7);
  await drag(MACRO, 0.2);
  later(SETTLE_MS);
  edits.undo();
  edits.undo();
  store.receive(values({ [MACRO]: 0.5, [LEVEL]: 0.3 })); // the echo of the undo, and another page
  later(SETTLE_MS);
  expect(edits.redo()).toBe("level · zoo was changed elsewhere: not redone");
  expect(edits.redo()).toBe("redid value · macro, to 0.200");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: MACRO, value: 0.2 });
});

test("an undo of a palette names the knob, not its value", async () => {
  const { edits, set } = setup();
  set(PALETTE, { label: "custom", stops: [{ at: 0, h: 0, s: 1, v: 1 }, { at: 1, h: 60, s: 1, v: 1 }] });
  expect(edits.undo()).toBe("undid palette · zoo");
});

test("undo sends the value before the edit as it was, not snapped to the knob's steps", async () => {
  const { store, sent, edits, set } = setup();
  store.receive(values({ [LEVEL]: 0.123456789 }));
  set(LEVEL, 0.2);
  expect(edits.undo()).toBe("undid level · zoo, back to 0.123");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.123456789 });
  expect(edits.redo()).toBe("redid level · zoo, to 0.200");
});

test("a colorway press is one step: undo puts back every knob it changed, redo sets them again", async () => {
  const { store, sent, edits, set, nextTask } = setup();
  set(LEVEL, 0.3);
  await nextTask();
  edits.sender.send({ type: "colorway", name: "red" });
  store.receive(values({ [LEVEL]: 0.8, "layers.base.zoo.color": { h: 0, s: 1, v: 1 } }));
  store.receive(aura({}, { colorway: "red" }));
  expect(edits.undo()).toBe("undid colorway red");
  expect(sets(sent).slice(-2)).toEqual([
    { type: "set", name: LEVEL, value: 0.3 },
    { type: "set", name: "layers.base.zoo.color", value: { h: 120, s: 1, v: 1 } },
  ]);
  edits.redo();
  expect(sets(sent).slice(-2).map((m) => m.value)).toEqual([0.8, { h: 0, s: 1, v: 1 }]);
  // A press of the colorway already active changes nothing: no step.
  edits.sender.send({ type: "colorway", name: "red" });
  edits.undo();
  expect(sets(sent).at(-1)!.value).toEqual({ h: 120, s: 1, v: 1 }); // the press undone, not a step for nothing
});

test("undoing every edit after a colorway press sends its values back exactly", async () => {
  const { store, sent, edits, set, nextTask } = setup();
  edits.sender.send({ type: "colorway", name: "red" });
  store.receive(values({ [LEVEL]: 0.8125 }));
  store.receive(aura({}, { colorway: "red" }));
  set(LEVEL, 0.4);
  await nextTask();
  set(MACRO, 0.2);
  edits.undo();
  edits.undo();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.8125 });
});

test("a new edit clears what redo holds", async () => {
  const { edits, set, nextTask } = setup();
  set(LEVEL, 0.6);
  await nextTask();
  edits.undo();
  expect(edits.can(false)).toBe(true);
  set(MACRO, 0.1);
  expect(edits.can(false)).toBe(false);
  expect(edits.redo()).toBeNull();
});

test("a recall, a revert, a surprise or a vary this page sends ends the history; a save, a rename or a change of the layers keeps it", async () => {
  type Case = (h: ReturnType<typeof setup>) => void;
  const ends: Case[] = [
    ({ edits }) => edits.sender.send({ type: "recall", name: "warm", fade: null }),
    ({ edits }) => edits.sender.send({ type: "look", look: {}, fade: null }),
    ({ edits }) => edits.sender.send({ type: "surprise", seed: null }),
    ({ edits }) => edits.sender.send({ type: "vary", strength: null, seed: null }),
  ];
  const keeps: Case[] = [
    ({ edits }) => edits.sender.send({ type: "save", name: "warm", fade: null, master: null }),
    ({ edits }) => edits.sender.send({ type: "keep" }),
    ({ store }) => store.receive(aura({ looks: { ...AURA.looks!, current: "cool", made: "surprise 3" } })),
    ({ store }) => store.receive(aura({}, { layers: [...AURA.stack.layers, { ...AURA.stack.layers[0]!, id: "top" }] })),
    ({ store }) => store.receive(aura({}, { layers: [{ ...AURA.stack.layers[0]!, id: "top" }, ...AURA.stack.layers] })),
    // A reconnect to the same look.
    ({ store }) => GREETING.forEach((msg) => store.receive(msg)),
  ];
  for (const [end, kept] of [...ends.map((c) => [c, false] as const), ...keeps.map((c) => [c, true] as const)]) {
    const h = setup();
    h.set(LEVEL, 0.6);
    await h.nextTask();
    h.set(MACRO, 0.1);
    h.edits.undo();
    expect([h.edits.can(true), h.edits.can(false)]).toEqual([true, true]);
    end(h);
    expect([h.edits.can(true), h.edits.can(false)]).toEqual([kept, kept]);
  }
});

test("a step for a knob that is gone is dropped", async () => {
  const { store, sent, edits, set, nextTask } = setup();
  set(LEVEL, 0.6);
  await nextTask();
  set(MACRO, 0.1);
  const declared = first("declare").params as readonly { name: string }[];
  store.receive({ type: "declare", params: declared.filter((p) => p.name !== MACRO) });
  edits.undo();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
  expect(edits.can(true)).toBe(false);
});

const button = (screen: Awaited<ReturnType<typeof renderWired>>["screen"], name: "undo" | "redo") =>
  screen.getByRole("button", { name, exact: true });

/** What the note under the look's header shows, or null while it is hidden. */
const headNote = () => {
  const note = document.querySelector<HTMLElement>(".look-head .disclosure-note");
  return note && !note.hidden ? note.textContent : null;
};

test("the look's header holds undo and redo: off with a reason, then each says what it did", async () => {
  const { screen, sent, receive } = await renderWired(
    <>
      <LookPanel />
      <StepStatus />
    </>,
    GREETING,
  );
  const undo = button(screen, "undo"), redo = button(screen, "redo");
  await expect.element(undo).toHaveAttribute("aria-disabled", "true");
  await expect.element(redo).toHaveAttribute("aria-disabled", "true");
  expect(undo.element().closest(".look-head .look-actions")).not.toBeNull();
  (undo.element() as HTMLElement).click(); // off, but it says why when pressed
  await expect.element(screen.getByText("no look edit to undo")).toBeVisible();
  await screen.getByRole("button", { name: "increase level" }).click();
  receive(values({ [LEVEL]: 0.505 }));
  await expect.element(undo).not.toHaveAttribute("aria-disabled");
  await undo.click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
  receive(values({ [LEVEL]: 0.5 }));
  await expect.poll(headNote).toBe("undid level · zoo, back to 0.500");
  await expect.element(screen.getByRole("status").filter({ hasText: "undid level · zoo, back to 0.500" }).first()).toBeInTheDocument();
  await expect.element(undo).toHaveAttribute("aria-disabled", "true");
  await redo.click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.505 });
  await expect.poll(headNote).toBe("redid level · zoo, to 0.505");
});

test("presses of a knob's keys or its + in a run are one undo step", async () => {
  const { screen, sent } = await renderWired(<LookPanel />, GREETING);
  (screen.getByRole("slider", { name: "level" }).element() as HTMLElement).focus();
  await userEvent.keyboard("{ArrowRight}{ArrowRight}{ArrowRight}{ArrowRight}{ArrowRight}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.525 });
  await button(screen, "undo").click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
  await expect.element(button(screen, "undo")).toHaveAttribute("aria-disabled", "true");
  const plus = screen.getByRole("button", { name: "increase level" });
  for (let i = 0; i < 3; i++) await plus.click();
  await button(screen, "undo").click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
  await expect.element(button(screen, "undo")).toHaveAttribute("aria-disabled", "true");
});

test("a colorway press is undone from the header, every knob it changed put back", async () => {
  const { screen, sent, receive } = await renderWired(<LookPanel />, GREETING);
  const chips = screen.getByRole("toolbar", { name: "colorways" });
  await chips.getByRole("button", { name: "red" }).click();
  receive(values({ [LEVEL]: 0.9 }));
  receive(aura({}, { colorway: "red" }));
  await button(screen, "undo").click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
});

test("mod+z undoes a look edit with focus on its knob or its entry once its typed value is sent, mod+shift+z and mod+y redo it; in typed text the keys are the text's", async () => {
  const { screen, sent, receive } = await renderWired(<LookPanel />, GREETING);
  const slider = screen.getByRole("slider", { name: "level" });
  (slider.element() as HTMLElement).focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.505 });
  receive(values({ [LEVEL]: 0.505 }));
  await userEvent.keyboard("{ControlOrMeta>}z{/ControlOrMeta}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.5 });
  receive(values({ [LEVEL]: 0.5 }));
  await userEvent.keyboard("{ControlOrMeta>}{Shift>}z{/Shift}{/ControlOrMeta}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.505 });
  receive(values({ [LEVEL]: 0.505 }));
  const entry = screen.getByRole("spinbutton", { name: "level" });
  await entry.click();
  await userEvent.keyboard("{ControlOrMeta>}a{/ControlOrMeta}0.7{Enter}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.7 });
  await userEvent.keyboard("{ControlOrMeta>}z{/ControlOrMeta}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.505 });
  await userEvent.keyboard("{ControlOrMeta>}y{/ControlOrMeta}");
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.7 });
  const count = sets(sent).length;
  await userEvent.keyboard("9");
  await userEvent.keyboard("{ControlOrMeta>}z{/ControlOrMeta}");
  expect(sets(sent)).toHaveLength(count);
  await expect.element(button(screen, "redo")).toHaveAttribute("aria-disabled", "true"); // nothing was undone
});

test("the keys are in the list, and in layout mode they are the layout editor's", async () => {
  function Layout() {
    const mode = useLayoutMode();
    return (
      <button type="button" onClick={() => mode.setOn(!mode.on)}>
        layout
      </button>
    );
  }
  const { screen } = await renderWired(
    <LayoutProvider>
      <Layout />
      <LookPanel />
      <ShortcutList />
    </LayoutProvider>,
    GREETING,
  );
  const list = screen.getByTestId("shortcuts");
  await expect.element(list.getByText("mod+z undo a look edit")).toBeInTheDocument();
  await expect.element(list.getByText("mod+shift+z redo a look edit")).toBeInTheDocument();
  await expect.element(list.getByText("mod+y redo a look edit")).toBeInTheDocument();
  await screen.getByRole("button", { name: "layout" }).click();
  await expect.element(list.getByText("mod+z undo a look edit")).not.toBeInTheDocument();
  await expect.element(list.getByText("mod+y redo a look edit")).not.toBeInTheDocument();
});

/** The registered shortcuts, each its keys and its label. */
function ShortcutList() {
  return (
    <ul data-testid="shortcuts">
      {useShortcutList().map((s) => (
        <li key={s.hotkey + s.label}>
          {s.hotkey} {s.label}
        </li>
      ))}
    </ul>
  );
}

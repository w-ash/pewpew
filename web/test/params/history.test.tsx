// The page's undo and redo of look edits: the history itself, on a store that heard the golden greeting,
// then its buttons and keys in the look's header.
import { expect, test } from "vitest";
import { userEvent } from "vitest/browser";
import type { AuraState } from "../../src/aura/aura";
import { LookPanel } from "../../src/deck/LookPanel";
import { useShortcutList } from "../../src/design/shortcuts";
import { StepStatus } from "../../src/design/StepStatus";
import { LayoutProvider, useLayoutMode } from "../../src/layout/LayoutMode";
import { EditHistory, GROUP_MS } from "../../src/params/history";
import type { ClientMessage, Sender, ServerMessage } from "../../src/wire/protocol";
import { WireStore } from "../../src/wire/store";
import { AURA, first, GREETING } from "../fixtures/messages";
import { renderWired } from "../harness";

const LEVEL = "layers.base.zoo.level";
const BANDS = "layers.base.zoo.bands";
const MACRO = "signals.macro.value";

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
  return { store, sent, edits, set, later, nextTask };
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
  const { sent, edits, set, later, nextTask } = setup();
  set(LEVEL, 0.6);
  edits.seal(LEVEL); // its control let go
  await nextTask();
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
  const step = edits.undo()!;
  expect(sets(sent).slice(-3)).toEqual([
    { type: "set", name: LEVEL, value: 0.9 },
    { type: "set", name: BANDS, value: 2 },
    { type: "set", name: MACRO, value: 0.5 },
  ]);
  expect(edits.told(step, true)).toBe("undid 3 knobs");
});

test("a step that ends where it began is not kept", async () => {
  const { edits, set } = setup();
  set(LEVEL, 0.7);
  set(LEVEL, 0.5); // a drag the browser took, put back
  edits.seal(LEVEL);
  expect(edits.can(true)).toBe(false);
  expect(edits.undo()).toBeNull();
});

test("undo sends the value before the edit as it was, not snapped to the knob's steps", async () => {
  const { store, sent, edits, set } = setup();
  store.receive(values({ [LEVEL]: 0.123456789 }));
  set(LEVEL, 0.2);
  const step = edits.undo()!;
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.123456789 });
  expect(edits.told(step, true)).toBe("undid level · zoo, back to 0.123");
  expect(edits.told(step, false)).toBe("redid level · zoo, to 0.200");
});

test("a colorway press is one step: undo puts back every knob it changed, redo sets them again", async () => {
  const { store, sent, edits, set, nextTask } = setup();
  set(LEVEL, 0.3);
  await nextTask();
  edits.sender.send({ type: "colorway", name: "red" });
  store.receive(values({ [LEVEL]: 0.8, "layers.base.zoo.color": { h: 0, s: 1, v: 1 } }));
  store.receive(aura({}, { colorway: "red" }));
  const step = edits.undo()!;
  expect(edits.told(step, true)).toBe("undid colorway red");
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

test("a recall, a save, another look or a change of the layers ends the history", async () => {
  const cases: ((h: ReturnType<typeof setup>) => void)[] = [
    ({ edits }) => edits.sender.send({ type: "recall", name: "warm", fade: null }),
    ({ edits }) => edits.sender.send({ type: "save", name: "warm", fade: null, master: null }),
    ({ store }) => store.receive(aura({ looks: { ...AURA.looks!, current: "cool" } })),
    ({ store }) => store.receive(aura({}, { layers: [...AURA.stack.layers, { ...AURA.stack.layers[0]!, id: "top" }] })),
  ];
  for (const end of cases) {
    const h = setup();
    h.set(LEVEL, 0.6);
    await h.nextTask();
    h.edits.undo();
    h.set(MACRO, 0.1);
    expect([h.edits.can(true), h.edits.can(false)]).toEqual([true, false]);
    h.edits.undo();
    end(h);
    expect([h.edits.can(true), h.edits.can(false)]).toEqual([false, false]);
  }
  // A reconnect to the same look keeps it.
  const h = setup();
  h.set(LEVEL, 0.6);
  for (const msg of GREETING) h.store.receive(msg);
  expect(h.edits.can(true)).toBe(true);
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
  await expect.element(screen.getByRole("status").filter({ hasText: "undid level · zoo, back to 0.500" })).toBeInTheDocument();
  await expect.element(undo).toHaveAttribute("aria-disabled", "true");
  await redo.click();
  expect(sets(sent).at(-1)).toEqual({ type: "set", name: LEVEL, value: 0.505 });
  await expect.element(screen.getByRole("status").filter({ hasText: "redid level · zoo, to 0.505" })).toBeInTheDocument();
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

test("mod+z undoes a look edit with focus on its knob, mod+shift+z redoes it; in typed text the keys are the text's", async () => {
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
  const count = sets(sent).length;
  const entry = screen.getByRole("spinbutton", { name: "level" });
  await entry.click();
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
  await expect.element(list.getByText("undo a look edit")).toBeInTheDocument();
  await expect.element(list.getByText("redo a look edit")).toBeInTheDocument();
  await screen.getByRole("button", { name: "layout" }).click();
  await expect.element(list.getByText("undo a look edit")).not.toBeInTheDocument();
});

/** The registered shortcuts' labels. */
function ShortcutList() {
  return (
    <ul data-testid="shortcuts">
      {useShortcutList().map((s) => (
        <li key={s.hotkey + s.label}>{s.label}</li>
      ))}
    </ul>
  );
}

// The layout editor and the report in the Console, on a page wired to the engine's golden messages
// (tests/goldens/wire.json): a run that takes `arrange`, its arrangement, report and power reading.
import { act } from "react";
import { afterEach, beforeEach, expect, onTestFinished, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { App } from "../../src/app/App";
import { EMPTY_ARRANGEMENT, useDoc } from "../../src/arrange/doc";
import { createHistory } from "../../src/arrange/history";
import { CHANGED_ELSEWHERE, SETTLE_MS } from "../../src/arrange/sync";
import type { Arrangement } from "../../src/arrange/types";
import { PARTS_URL } from "../../src/rig/loadParts";
import { dragPreview } from "../../src/rig3d/dragPreview";
import { commitDrag } from "../../src/rig3d/Stage3D";
import { Matrix4, Vector3 } from "three";
import type { ClientMessage, ServerMessage } from "../../src/wire/protocol";
import { first, GREETING, hello, LATER } from "../fixtures/messages";
import { renderWired } from "../harness";
import { partsCatalog } from "../studio/fixtures/rig";

/** The golden run: a rig (the later layout) whose hello offers "arrange". */
const RIG_RUN: readonly ServerMessage[] = [...GREETING, first("layout", LATER)];
const ENGINE = first("arrangement").arrangement!;
const BASE = first("arrangement").base!;
const REFUSED = LATER.find((m) => m.type === "refused" && m.control === "arrange")!;

const arranges = (sent: readonly ClientMessage[]) =>
  sent.filter((m): m is Extract<ClientMessage, { type: "arrange" }> => m.type === "arrange");

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

async function openLayout(heard: readonly ServerMessage[] = RIG_RUN) {
  const wired = await renderWired(<App />, heard);
  await wired.screen.getByRole("button", { name: "layout" }).click();
  return wired;
}

test("on a run that takes `arrange`, the layout panel holds the tools and the engine's arrangement", async () => {
  const { screen } = await openLayout();
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByRole("button", { name: "blink" })).toBeVisible();
  await expect.element(panel.getByTestId("entity-list").getByRole("button", { name: /^a/ })).toBeVisible();
  expect(useDoc.getState().history.present.fixtures.map((f) => f.id)).toEqual(["a"]);
});

test("without the capability (an unattended run), the layout panel has the tools and no editor", async () => {
  const noCapability = RIG_RUN.map((m) => (m.type === "hello" ? hello({ capabilities: ["ack"] }) : m));
  const { screen } = await openLayout(noCapability);
  await expect.element(screen.getByRole("button", { name: "blink" })).toBeVisible();
  await expect.element(screen.getByTestId("entity-list")).not.toBeInTheDocument();
});

test("without a rig, the layout panel has no editor", async () => {
  const { screen } = await openLayout(GREETING);
  await expect.element(screen.getByText(/layout tools need an arrangement/)).toBeVisible();
  await expect.element(screen.getByTestId("entity-list")).not.toBeInTheDocument();
});

test("quick edits send exactly one `arrange` once they settle, with the last of them", async () => {
  const { screen, sent } = await openLayout();
  const name = screen.getByRole("textbox", { name: "Name" });
  await name.click();
  await userEvent.keyboard("abc");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1);
  // The file's own form: no empty `groups` list where the file had none, built on the engine's file.
  expect(arranges(sent)[0]!.arrangement).toEqual({ ...ENGINE, name: "abc" });
  expect(arranges(sent)[0]!.base).toBe(BASE);
});

test("the engine's echo keeps the undo history; an arrangement from elsewhere replaces it", async () => {
  const { screen, sent, receive, answer } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("mine");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  await answer(true);
  receive({ type: "arrangement", arrangement: arranges(sent)[0]!.arrangement, base: "b1" });
  const undo = screen.getByRole("button", { name: "Undo" });
  await expect.element(undo).toBeEnabled();

  const other: Arrangement = { ...ENGINE, name: "saved by hand" } as Arrangement;
  receive({ type: "arrangement", arrangement: other, base: "b2" });
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("saved by hand");
  await expect.element(undo).toBeDisabled();
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1); // the engine's own arrangement is never sent back
});

test("undo sends the arrangement it restores, and a refusal shows the engine's reason and issues", async () => {
  const { screen, sent, receive, answer } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("bad");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  receive(REFUSED);
  await answer(false);
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByText(/The engine did not take this edit: the arrangement does not compile/)).toBeVisible();
  await expect.element(panel.getByText(/^no fixture 'ghost'/)).toBeVisible();

  await screen.getByRole("button", { name: "Undo" }).click();
  // The engine still holds its own arrangement, which the undo restores: nothing to send.
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1);
});

test("the editor's keys work only while the layout panel is open", async () => {
  const { screen } = await renderWired(<App />, RIG_RUN);
  await userEvent.keyboard("?");
  await expect.element(screen.getByText("undo")).not.toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  await screen.getByRole("button", { name: "layout" }).click();
  await expect.element(screen.getByRole("region", { name: "layout" })).toBeVisible();
  await screen.getByRole("textbox", { name: "Name" }).fill("x");
  (document.activeElement as HTMLElement | null)?.blur();
  await userEvent.keyboard("{ControlOrMeta>}z{/ControlOrMeta}");
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("");
});

test("the report shows the rig's report, its issues and the engine's live watts", async () => {
  const { screen } = await openLayout();
  await screen.getByRole("region", { name: "layout" }).getByRole("button", { name: /^report/ }).click();
  const report = screen.getByRole("region", { name: "report" });
  await expect.element(report.getByRole("region", { name: "Summary" })).toBeVisible();
  const power = first("power");
  const watts = report.getByTestId("report-watts");
  await expect.poll(() => watts.element().textContent).toContain(`${power.watts.toFixed(1)} W`);
  await expect.poll(() => watts.element().textContent).toContain(`${power.uncapped_watts.toFixed(1)} W uncapped`);
  await expect.element(report.getByRole("switch", { name: "Cap the watts" })).toBeVisible();
  await screen.getByRole("button", { name: "close report" }).click();
  await expect.element(screen.getByRole("region", { name: "layout" })).toBeVisible();
});

test("with the layout panel open, the 3D view edits the selected fixture with a gizmo, and only then", async () => {
  const { screen } = await renderWired(<App />, RIG_RUN);
  await screen.getByRole("radiogroup", { name: "Stage view" }).getByText("3D", { exact: true }).click();
  await expect.element(screen.getByRole("img", { name: "3D preview of the LEDs" })).toBeInTheDocument();
  useDoc.getState().select({ kind: "fixture", id: "a" });
  await expect.element(screen.getByRole("radiogroup", { name: "Gizmo" })).not.toBeInTheDocument();
  await screen.getByRole("button", { name: "layout" }).click();
  await screen.getByTestId("entity-list").getByRole("button", { name: /^a/ }).click();
  await expect.element(screen.getByRole("radiogroup", { name: "Gizmo" })).toBeVisible();
  await screen.getByRole("button", { name: "close layout" }).click();
  await expect.element(screen.getByRole("radiogroup", { name: "Gizmo" })).not.toBeInTheDocument();
});

test("an edit made while one is in flight waits for its echo, and goes on the base the echo names", async () => {
  const { screen, sent, receive, answer } = await openLayout();
  const name = screen.getByRole("textbox", { name: "Name" });
  await name.fill("one");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  await name.fill("two");
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1); // the first is not answered yet
  await answer(true);
  receive({ type: "arrangement", arrangement: arranges(sent)[0]!.arrangement, base: "b1" });
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(2);
  expect(arranges(sent)[1]).toMatchObject({ base: "b1", arrangement: { name: "two" } });
});

test("a refusal of a stale edit shows the engine's current layout in its place", async () => {
  const { screen, sent, receive, answer } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("mine");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  // Another tab's edit landed first; the engine refuses this one and sends its own.
  receive({ type: "refused", control: "arrange", name: null, id: null, reason: "the layout changed; showing the current one" });
  await answer(false);
  receive({ type: "arrangement", arrangement: { ...ENGINE, name: "theirs" } as Arrangement, base: "b2" });
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByText(CHANGED_ELSEWHERE)).toBeVisible();
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("theirs");
  await expect.element(screen.getByRole("button", { name: "Undo" })).toBeDisabled();
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1);
});

/** The engine's greeting on a new connection, up to its arrangement: its hello, and its rig's layout. */
function reconnect(receive: (msg: ServerMessage) => void): void {
  receive(hello());
  receive(first("layout", LATER));
}

test("after a reconnect to the same file, the history stays and the edit not taken goes again", async () => {
  const { screen, store, sent, receive, answer } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("mine");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  // The connection drops with the edit unanswered: the socket settles its ask untaken, with no refusal.
  act(() => store.disconnected());
  await answer(false);
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByText(/Reconnecting to the engine: the layout is read-only/)).toBeVisible();
  // No edit is taken while it is down, from a key or otherwise.
  await userEvent.keyboard("{ControlOrMeta>}z{/ControlOrMeta}");
  useDoc.getState().commit({ ...useDoc.getState().history.present, name: "offline" });
  expect(useDoc.getState().history.present.name).toBe("mine");
  // The engine is back on the same file: the history stays, and the present goes again on that file.
  reconnect(receive);
  receive(first("arrangement"));
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(2);
  expect(arranges(sent)[1]).toMatchObject({ base: BASE, arrangement: { name: "mine" } });
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("mine");
  await expect.element(screen.getByRole("button", { name: "Undo" })).toBeEnabled();
  await expect.element(panel.getByText(CHANGED_ELSEWHERE)).not.toBeInTheDocument();
});

test("after a reconnect to an engine that took the edit in flight, the history stays and a later edit goes on it", async () => {
  const { screen, store, sent, receive, answer } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("A");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  // B is edited while A is unanswered; the connection drops before A's echo.
  await screen.getByRole("textbox", { name: "Name" }).fill("B");
  act(() => store.disconnected());
  await answer(false);
  reconnect(receive);
  // The engine applied A.
  receive({ type: "arrangement", arrangement: arranges(sent)[0]!.arrangement, base: "bA" });
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(2);
  expect(arranges(sent)[1]).toMatchObject({ base: "bA", arrangement: { name: "B" } });
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByText(CHANGED_ELSEWHERE)).not.toBeInTheDocument();
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("B");
  await expect.element(screen.getByRole("button", { name: "Undo" })).toBeEnabled();
});

test("after a reconnect to a file changed meanwhile, its layout replaces the edit not taken, with a notice", async () => {
  const { screen, store, sent, receive, answer } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("mine");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  act(() => store.disconnected());
  await answer(false);
  reconnect(receive);
  receive({ type: "arrangement", arrangement: { ...ENGINE, name: "saved by hand" } as Arrangement, base: "b9" });
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByText(CHANGED_ELSEWHERE)).toBeVisible();
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("saved by hand");
  await expect.element(screen.getByRole("button", { name: "Undo" })).toBeDisabled();
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1);
  // The next edit is news of its own.
  await screen.getByRole("textbox", { name: "Name" }).fill("again");
  await expect.element(panel.getByText(CHANGED_ELSEWHERE)).not.toBeInTheDocument();
});

test("a layout from elsewhere with no edit waiting replaces the history without a notice", async () => {
  const { screen, receive } = await openLayout();
  receive({ type: "arrangement", arrangement: { ...ENGINE, name: "other tab" } as Arrangement, base: "b2" });
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("other tab");
  await expect.element(screen.getByText(CHANGED_ELSEWHERE)).not.toBeInTheDocument();
});

test("a stale refusal that carries the engine's layout shows it with no broadcast after it", async () => {
  const { screen, sent, receive, answer } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("mine");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  receive({
    type: "refused", control: "arrange", name: null, id: null, reason: "the layout changed; showing the current one",
    arrangement: { ...ENGINE, name: "theirs" } as Arrangement, base: "b2",
  });
  await answer(false);
  await expect.element(screen.getByRole("textbox", { name: "Name" })).toHaveValue("theirs");
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByText(CHANGED_ELSEWHERE)).toBeVisible();
  await expect.element(panel.getByText(/The engine did not take this edit/)).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "Undo" })).toBeDisabled();
  // The next edit builds on the file the refusal named.
  await screen.getByRole("textbox", { name: "Name" }).fill("mine again");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(2);
  expect(arranges(sent)[1]).toMatchObject({ base: "b2", arrangement: { name: "mine again" } });
});

test("a refused edit goes again on `send again`, or on an undo and a redo, never by itself", async () => {
  const { screen, sent, receive, answer } = await openLayout();
  const late = { type: "refused", control: "arrange", name: null, id: null,
    reason: "the engine is busy, so the layout did not change; send it again" } as const;
  await screen.getByRole("textbox", { name: "Name" }).fill("busy");
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  receive(late);
  await answer(false);
  const panel = screen.getByRole("region", { name: "layout" });
  await expect.element(panel.getByText(/the engine is busy/)).toBeVisible();
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1);
  await panel.getByRole("button", { name: "send again" }).click();
  await expect.poll(() => arranges(sent).length).toBe(2);
  expect(arranges(sent)[1]).toMatchObject({ base: BASE, arrangement: { name: "busy" } });
  receive(late);
  await answer(false);
  await screen.getByRole("button", { name: "Undo" }).click();
  await screen.getByRole("button", { name: "Redo" }).click();
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(3);
  expect(arranges(sent)[2]).toMatchObject({ base: BASE, arrangement: { name: "busy" } });
});

test("switching to the report while an edit settles sends it once and keeps its undo", async () => {
  const { screen, sent } = await openLayout();
  await screen.getByRole("textbox", { name: "Name" }).fill("moved");
  await screen.getByRole("region", { name: "layout" }).getByRole("button", { name: /^report/ }).click();
  await expect.element(screen.getByRole("region", { name: "report" })).toBeVisible();
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1);
  await new Promise((r) => setTimeout(r, SETTLE_MS * 2));
  expect(arranges(sent)).toHaveLength(1);
  expect(arranges(sent)[0]).toMatchObject({ base: BASE, arrangement: { name: "moved" } });
  expect(useDoc.getState().history.past).toHaveLength(1);
  await screen.getByRole("button", { name: "close report" }).click();
  await expect.element(screen.getByRole("button", { name: "Undo" })).toBeEnabled();
});

test("once the engine offers no arrangement to edit, the editor closes", async () => {
  const { screen, receive } = await openLayout();
  await expect.element(screen.getByTestId("entity-list")).toBeVisible();
  receive({ type: "arrangement", arrangement: null, base: null });
  await expect.element(screen.getByTestId("entity-list")).not.toBeInTheDocument();
});

test("Backspace deletes the selected fixture only after a press in the editor, never after one elsewhere", async () => {
  // WebKit takes a Backspace no handler prevents as "back", which would leave the test page.
  const stay = (e: KeyboardEvent) => e.key === "Backspace" && e.preventDefault();
  window.addEventListener("keydown", stay);
  onTestFinished(() => window.removeEventListener("keydown", stay));
  const { screen } = await renderWired(<App />, RIG_RUN);
  await screen.getByRole("radiogroup", { name: "Stage view" }).getByText("3D", { exact: true }).click();
  await screen.getByRole("button", { name: "layout" }).click();
  const entity = screen.getByTestId("entity-list").getByRole("button", { name: /^a/ });
  const ids = () => useDoc.getState().history.present.fixtures.map((f) => f.id);
  const select = async () => {
    await entity.click();
    expect(useDoc.getState().selection).toEqual({ kind: "fixture", id: "a" });
  };
  // A press on a deck button, whether or not it takes focus (Safari's does not), or on the page outside
  // the editor, ends the editor's turn.
  await select();
  await screen.getByRole("button", { name: "blackout" }).click();
  await userEvent.keyboard("{Backspace}");
  expect(ids()).toEqual(["a"]);
  await select();
  await screen.getByRole("region", { name: "layout" }).getByRole("heading", { name: "layout" }).click();
  await userEvent.keyboard("{Backspace}");
  expect(ids()).toEqual(["a"]);
  await select();
  await userEvent.click(document.body, { position: { x: 1, y: 1 } });
  await userEvent.keyboard("{Delete}");
  expect(ids()).toEqual(["a"]);
  // A press on the 3D view gives it back.
  await select();
  await screen.getByRole("img", { name: "3D preview of the LEDs" }).click();
  useDoc.getState().select({ kind: "fixture", id: "a" }); // whatever the press picked
  await userEvent.keyboard("{Backspace}");
  expect(ids()).toEqual([]);
});

/** Where the 3D view draws fixture `id` of the rig: its server matrix moved by its offset, if any. */
function drawnAt(store: { getState(): { map: { rig?: { fixtures: readonly { id: string; matrix: readonly number[] }[] } | null } | null } }, id: string) {
  const fixtures = store.getState().map?.rig?.fixtures ?? [];
  const i = fixtures.findIndex((f) => f.id === id);
  const m = new Matrix4().fromArray(fixtures[i]!.matrix);
  const offset = dragPreview.offsets?.get(i);
  if (offset) m.premultiply(offset);
  return new Vector3().setFromMatrixPosition(m).toArray().map((v) => Math.round(v * 1e4) / 1e4);
}

test("the 3D view draws the editor's poses: a drag ends as it commits, and an undo in flight shows at once", async () => {
  const { screen, store, sent } = await renderWired(<App />, RIG_RUN);
  await screen.getByRole("radiogroup", { name: "Stage view" }).getByText("3D", { exact: true }).click();
  await screen.getByRole("button", { name: "layout" }).click();
  await screen.getByTestId("entity-list").getByRole("button", { name: /^a/ }).click();
  await expect.element(screen.getByRole("radiogroup", { name: "Gizmo" })).toBeVisible();
  const a = { kind: "fixture", id: "a" } as const;
  const engineAt = drawnAt(store, "a");
  dragPreview.begin([0]);
  dragPreview.move(new Matrix4().makeTranslation(1, 0, 0));
  commitDrag(a, { position_m: [1, 0, 0], quat_xyzw: [0, 0, 0, 1] });
  expect(dragPreview.delta).toBeNull(); // the drag's own preview ends: the editor's pose takes over
  expect(drawnAt(store, "a")).toEqual([1, 0, 0]);
  await expect.poll(() => arranges(sent).length, { timeout: SETTLE_MS * 4 }).toBe(1); // in flight, no echo yet
  commitDrag(a, { position_m: [1, 2, 0], quat_xyzw: [0, 0, 0, 1] });
  expect(drawnAt(store, "a")).toEqual([1, 2, 0]);
  useDoc.getState().undo();
  expect(drawnAt(store, "a")).toEqual([1, 0, 0]); // at once, not at the engine's echo
  useDoc.getState().undo();
  expect(drawnAt(store, "a")).toEqual(engineAt);
  // The editor closed, the view draws the engine's compile.
  useDoc.getState().redo();
  await screen.getByRole("button", { name: "close layout" }).click();
  await expect.poll(() => dragPreview.offsets).toBeNull();
});

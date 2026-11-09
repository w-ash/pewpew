import { act, type ReactNode } from "react";
import { expect, test } from "vitest";
import { page, userEvent } from "vitest/browser";
import type { AuraState } from "../../src/aura/aura";
import { App } from "../../src/app/App";
import { StepStatus } from "../../src/design/StepStatus";
import { ArmStatus } from "../../src/design/press";
import { Deck } from "../../src/deck/Deck";
import { looksAbout } from "../../src/deck/Looks";
import { LookPanel } from "../../src/deck/LookPanel";
import { barLines, failedText, StatusBar } from "../../src/status/StatusBar";
import { greeting, hello, refused, AURA } from "../fixtures/messages";
import { Layers, pastDoubleTap, renderWired } from "../harness";

const aura = (patch: Partial<AuraState>) => ({ type: "aura" as const, ...AURA, ...patch });

function Played() {
  return <Deck />;
}

/** The editor's look and layers, as the slot shows them. */
function Editor() {
  return (
    <>
      <LookPanel />
      <Layers />
    </>
  );
}

/** `ui` (the editor alone unless given) with "save as new…" open, from the look's settings. */
async function saving(ui: ReactNode = <Editor />) {
  const wired = await renderWired(ui);
  await wired.screen.getByRole("button", { name: "look settings" }).click();
  await wired.screen.getByRole("button", { name: "save as new…" }).click();
  return wired;
}

test("blackout takes two presses; restore takes one", async () => {
  const { screen, sent, receive } = await renderWired(<Played />);
  await screen.getByRole("button", { name: "blackout" }).click();
  expect(sent).toEqual([]);
  const armed = screen.getByRole("button", { name: "again to black out" });
  await armed.click();
  expect(sent).toEqual([]);
  pastDoubleTap();
  await armed.click();
  expect(sent).toEqual([{ type: "blackout", on: true }]);
  receive(aura({ blackout: true }));
  await screen.getByRole("button", { name: "restore" }).click();
  expect(sent.at(-1)).toEqual({ type: "blackout", on: false });
});

test("the room going black and coming back is said, as the button's new name may not be", async () => {
  const { receive } = await renderWired(
    <>
      <Played />
      <StepStatus />
    </>,
  );
  const said = () => [...document.querySelectorAll(".sr-only[role=status]")].at(-1)?.textContent;
  receive(aura({ blackout: true }));
  await expect.poll(said).toBe("room blacked out");
  receive(aura({ blackout: false }));
  await expect.poll(said).toBe("room restored");
});

test("B twice blacks out, Esc disarms", async () => {
  const { screen, sent } = await renderWired(<App />);
  await userEvent.keyboard("b");
  await expect.element(screen.getByRole("button", { name: "again to black out" })).toBeVisible();
  await userEvent.keyboard("{Escape}");
  // No arm lapses on the test clock: the disarm is Esc's.
  await expect.element(screen.getByRole("button", { name: "blackout" })).toBeVisible();
  await userEvent.keyboard("b");
  pastDoubleTap();
  await userEvent.keyboard("b");
  expect(sent).toEqual([{ type: "blackout", on: true }]);
});

/** The deck's "⋯", which opens what is rarely needed and what each row does. */
const MORE = "more: cues, fade and what these do";

test("cues on, behind the ⋯, is one press, off two; the cue buttons show only while they are on", async () => {
  // Docked low, as on a phone: the note opens over what is above the deck.
  const { screen, sent, receive } = await renderWired(
    <div style={{ paddingTop: 480 }}>
      <Played />
    </div>,
  );
  await expect.element(screen.getByRole("button", { name: "door" })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "cues on" })).not.toBeInTheDocument(); // hidden behind the ⋯
  await screen.getByRole("button", { name: MORE }).click();
  await expect.element(screen.getByText(/a cue plays a look briefly, then comes back/)).toBeVisible();
  await screen.getByRole("button", { name: "cues on" }).click();
  expect(sent).toEqual([{ type: "arm", on: true }]);
  receive(aura({ triggers: { ...AURA.triggers!, armed: true } }));
  await screen.getByRole("button", { name: "door" }).click();
  expect(sent.at(-1)).toEqual({ type: "fire", name: "door", value: null });
  const arm = screen.getByRole("button", { name: "cues on" });
  await expect.element(arm).toHaveAttribute("aria-pressed", "true");
  await arm.click();
  expect(sent.at(-1)?.type).toBe("fire");
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to turn off" }).click();
  expect(sent.at(-1)).toEqual({ type: "arm", on: false });
});

test("on a phone the cue buttons keep their width, and an outcome or a countdown moves nothing", async () => {
  await page.viewport(390, 844);
  const { receive } = await renderWired(<Played />);
  const triggers = { ...AURA.triggers!, armed: true, names: ["front door", "back door"] };
  receive(aura({ triggers }));
  const visible = () => {
    const row = document.querySelector(".cues .scroller")!.getBoundingClientRect();
    return [...document.querySelectorAll(".cues .cue")].every((b) => b.getBoundingClientRect().right <= row.right + 1);
  };
  await expect.poll(visible).toBe(true);
  const shape = () => [document.querySelector(".deck")!.getBoundingClientRect().height, document.querySelector(".cue")!.getBoundingClientRect().width];
  const before = shape();
  receive(aura({ triggers: { ...triggers, last: { name: "front door", fired: false, reason: "disarmed", error: null } } }));
  await expect.poll(() => document.querySelector(".cues .last [role=status]")?.textContent).toBe("front door: cues off");
  receive(aura({ triggers: { ...triggers, held: { trigger: "front door", look: "cool", until: 9 } } }));
  await expect.poll(() => document.querySelector(".cue")?.textContent).toMatch(/^front door · /);
  expect(shape()).toEqual(before);
  expect(visible()).toBe(true);
  await page.viewport(414, 896);
});

test("beside the cues, what each does stays; an outcome takes its room only once judged while they show", async () => {
  const { receive } = await renderWired(<Played />);
  const fired = { name: "door", fired: true, reason: null, error: null };
  // Fired before this page armed them: old news, never shown.
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, last: fired } }));
  const does = () => document.querySelector(".cue-does");
  const said = () => document.querySelector(".cues .last [role=status]")?.textContent;
  await expect.poll(() => does()?.textContent).toMatch(/^door → /);
  expect(said()).toBe("");
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, last: { ...fired, name: "bell" } } }));
  await expect.poll(said).toMatch(/^bell /);
  expect(does()?.hasAttribute("data-out")).toBe(true); // in the same room, so nothing moves
  receive(aura({ triggers: { ...AURA.triggers!, armed: false, last: { ...fired, name: "bell" } } }));
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, last: { ...fired, name: "bell" } } }));
  await expect.poll(said).toBe(""); // armed again: the outcome is gone
});

test("the arm switch is absent with no trigger to arm", async () => {
  const { screen, receive } = await renderWired(<Played />);
  receive(aura({ triggers: { armed: false, names: [], cues: {}, held: null, last: null } }));
  await expect.element(screen.getByRole("button", { name: "blackout" })).toBeVisible();
  expect(screen.getByRole("button", { name: /^triggers/ }).query()).toBeNull();
});

test("the live look is scrolled into view in its row, and only the row moves", async () => {
  const items = Array.from({ length: 12 }, (_, i) => ({ name: `look${i}`, fade: 1, cycle: false, master: false }));
  const { screen, receive } = await renderWired(
    <div className="panel" style={{ width: 320, height: 60, overflowY: "auto" }}>
      <Played />
    </div>,
  );
  const panel = document.querySelector<HTMLElement>(".panel")!;
  panel.scrollTop = panel.scrollHeight;
  const scrolled = panel.scrollTop;
  receive(aura({ looks: { ...AURA.looks!, items, favorites: items.map((i) => i.name), current: "look7" } })); // one look follows it: the deck shows nine
  const item = screen.getByRole("button", { name: "look7" }).element();
  const row = item.closest(".scroller")!;
  // Clear of the row's 16 px fade at its end, which more looks follow.
  await expect.poll(() => item.getBoundingClientRect().right <= row.getBoundingClientRect().right - 15).toBe(true);
  expect(row.scrollLeft).toBeGreaterThan(0);
  expect(scrolled).toBeGreaterThan(0);
  expect(panel.scrollTop).toBe(scrolled);
});

test("a cue's held look is lit, and the current one shows the aura returns to it", async () => {
  const { screen, receive } = await renderWired(<Played />);
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, held: { trigger: "door", look: "cool", until: 9 } } }));
  await expect.element(screen.getByRole("button", { name: "cool" })).toHaveAttribute("aria-pressed", "true");
  const warm = screen.getByRole("button", { name: /^warm/ });
  await expect.element(warm).toHaveAttribute("data-returns");
  await expect.element(warm).toHaveAttribute("aria-pressed", "false");
});

test("a cue's hold takes focus from the control it makes wait to the hold's note, and gives it back when it ends", async () => {
  const { screen, receive } = await renderWired(<App />);
  const add = screen.getByRole("button", { name: "+ layer" });
  add.element().focus();
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, held: { trigger: "door", look: "cool", until: 9 } } }));
  await expect.element(screen.getByText("door is playing cool: edit when it ends")).toHaveFocus();
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, held: null } }));
  await expect.element(add).toHaveFocus();
});

test("focus on a knob when the connection is lost comes back to that knob once the engine is back", async () => {
  const { screen, store, receive } = await renderWired(<App />);
  const bands = screen.getByRole("spinbutton", { name: "bands" });
  bands.element().focus();
  act(() => store.disconnected());
  // The engine's greeting comes over a few frames: the knob is back only after its hello.
  const [hi, ...rest] = greeting();
  receive(hi!);
  await expect.element(screen.getByRole("heading", { name: "warm" })).toHaveFocus(); // meanwhile on the look
  for (const msg of rest) receive(msg);
  await expect.element(screen.getByRole("spinbutton", { name: "bands" })).toHaveFocus();
});

test("looks recall over the chosen fade, by tap and by number key", async () => {
  await page.viewport(1280, 800);
  const { screen, sent } = await renderWired(<Played />);
  await screen.getByRole("button", { name: "cool" }).click();
  expect(sent.at(-1)).toEqual({ type: "recall", name: "cool", fade: null });
  await screen.getByRole("button", { name: MORE }).click();
  await screen.getByRole("combobox", { name: "fade into a look" }).selectOptions("fade: 2 s");
  await userEvent.keyboard("2"); // alphabetical: cool is 1
  expect(sent.at(-1)).toEqual({ type: "recall", name: "warm", fade: 2 });
  // The fade chosen is the page's, not the deck's: the list of every look takes it too. Put it back.
  await screen.getByRole("combobox", { name: "fade into a look" }).selectOptions("fade: as saved");
  await page.viewport(414, 896);
});

test("the saved looks are one tab stop: the arrows move between them", async () => {
  const { screen } = await renderWired(<Played />);
  const warm = screen.getByRole("button", { name: /^warm/ });
  await expect.element(warm).toHaveAttribute("tabindex", "0");
  await expect.element(screen.getByRole("button", { name: "cool" })).toHaveAttribute("tabindex", "-1");
  warm.element().focus();
  await userEvent.keyboard("{ArrowLeft}");
  await expect.element(screen.getByRole("button", { name: "cool" })).toHaveFocus();
  await userEvent.keyboard("{End}");
  await expect.element(warm).toHaveFocus();
});

test("the looks' legend names only the signs shown now, each with its icon", () => {
  const looks = AURA.looks!;
  const item = (name: string, cycle: boolean) => ({ name, cycle, fade: 2 });
  const held = { ...AURA.triggers!, armed: true, held: { trigger: "door", look: "cool", until: 9 } };
  expect(looksAbout({ ...looks, items: [] }, null)).toEqual([]);
  expect(looksAbout({ ...looks, changed: true, items: [item("warm", true)] }, AURA.triggers)).toEqual([]); // nothing marked: "changed" is the header's
  expect(looksAbout({ ...looks, items: [item("warm", true), item("cool", true)] }, held)).toEqual([{ icon: "return", text: "returns here after the cue" }]);
  expect(looksAbout({ ...looks, items: [item("warm", true), item("cool", false)] }, null)).toEqual([{ icon: "cycle", text: "in shuffle" }]);
  expect(looksAbout({ ...looks, items: [item("warm", true), item("cool", false), item("tide", true)] }, null)).toEqual([
    { icon: "cycle", slashed: true, text: "not in shuffle" },
  ]);
});

test("arming cues and a cue's hold move no chip: ↩ lies in the current look's corner", async () => {
  await page.viewport(1440, 900);
  const items = Array.from({ length: 9 }, (_, i) => ({ name: `look-${"x".repeat(i % 4)}${i}`, cycle: true, fade: 2 }));
  const { receive } = await renderWired(
    <div data-wide="" style={{ width: 460 }}>
      <Played />
    </div>,
  );
  receive(aura({ looks: { ...AURA.looks!, items, favorites: items.map((i) => i.name), current: "look-0" } }));
  const chips = () => [...document.querySelectorAll(".looks .tile")].map((b) => {
    const r = b.getBoundingClientRect();
    return `${r.left},${r.top},${r.width}`;
  });
  await expect.poll(() => chips().length).toBe(9);
  const unarmed = chips();
  const armed = { ...AURA.triggers!, armed: true };
  receive(aura({ looks: { ...AURA.looks!, items, favorites: items.map((i) => i.name), current: "look-0" }, triggers: armed }));
  await expect.poll(() => document.querySelectorAll(".cue").length).toBe(2);
  expect(chips()).toEqual(unarmed);
  const shape = () => [document.querySelector(".deck")!.getBoundingClientRect().height, ...chips()];
  const before = shape();
  receive(aura({ looks: { ...AURA.looks!, items, favorites: items.map((i) => i.name), current: "look-0" }, triggers: { ...armed, held: { trigger: "door", look: "look-3", until: 9 } } }));
  await expect.poll(() => document.querySelector(".tile[data-returns] .returns")).not.toBeNull();
  expect(document.querySelectorAll(".returns").length).toBe(1);
  expect(shape()).toEqual(before);
  await page.viewport(414, 896);
});

test("↻ marks the fewer: the looks shuffle plays, or, slashed, those it leaves out", async () => {
  const { screen, receive } = await renderWired(<Played />);
  const item = (name: string, cycle: boolean) => ({ name, cycle, fade: 2 });
  receive(aura({ looks: { ...AURA.looks!, items: [item("warm", true), item("cool", false), item("tide", true)], favorites: ["warm", "cool", "tide"] } }));
  await expect.element(screen.getByRole("button", { name: "cool, not in shuffle" })).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "tide" })).toBeVisible();
  expect(document.querySelectorAll(".looks .cyc").length).toBe(1);
  expect(document.querySelector(".looks .cyc")?.hasAttribute("data-out")).toBe(true);
});

test("an armed button says what its second press does in the page's status; disarmed, the line goes", async () => {
  const { screen } = await renderWired(
    <>
      <Played />
      <ArmStatus />
    </>,
  );
  const line = screen.getByRole("status").filter({ hasText: "press again to black out" });
  await screen.getByRole("button", { name: "blackout" }).click();
  await expect.element(line).toBeInTheDocument();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to black out" }).click();
  await expect.element(line).not.toBeInTheDocument();
});

test("Esc in the deck's ⋯ note closes it and hands focus back to the ⋯, which names only what its note holds", async () => {
  const { screen, receive } = await renderWired(<Played />);
  const more = screen.getByRole("button", { name: MORE });
  await more.click();
  (screen.getByRole("button", { name: "cues on" }).element() as HTMLElement).focus();
  await userEvent.keyboard("{Escape}");
  await expect.element(more).toHaveAttribute("aria-expanded", "false");
  await expect.element(more).toHaveFocus();
  receive(aura({ looks: null }));
  await expect.element(screen.getByRole("button", { name: "more: cues and what these do" })).toBeVisible();
  // With nothing behind it there is no ⋯, rather than one that opens an empty note.
  receive(aura({ looks: null, triggers: null }));
  await expect.element(screen.getByRole("button", { name: /^more/ })).not.toBeInTheDocument();
});

test("↻ marks the looks shuffle plays, for assistive tech in words, only when some are left out", async () => {
  const { screen, receive } = await renderWired(<Played />);
  await expect.element(screen.getByRole("button", { name: "warm, in shuffle" })).toBeVisible();
  receive(aura({ looks: { ...AURA.looks!, items: AURA.looks!.items.map((item) => ({ ...item, cycle: true })) } }));
  await expect.element(screen.getByRole("button", { name: "warm", exact: true })).toBeVisible();
  expect(document.querySelector(".looks .cyc")).toBeNull();
});

test("save shows only while there is something to save; a changed look saves into itself in one press; its ▾ saves as new", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  const save = screen.getByRole("button", { name: "save", exact: true });
  await expect.element(save).not.toBeInTheDocument(); // warm plays as saved
  await expect.element(screen.getByRole("button", { name: "save as new…" })).not.toBeInTheDocument();
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  await save.click();
  expect(sent).toEqual([{ type: "save", name: "warm", fade: null, master: null }]); // one press; its own fade and brightness choice kept
  expect(document.querySelectorAll('.look-head [data-variant="primary"]:not([data-square])')).toHaveLength(1);
  await screen.getByRole("button", { name: "save as new…" }).click();
  await screen.getByRole("textbox", { name: "look name" }).fill("new one");
  screen.getByRole("textbox", { name: "look name" }).element().focus();
  await userEvent.keyboard("{Enter}");
  expect(sent.at(-1)).toEqual({ type: "save", name: "new one", fade: null, master: true });
});

test("save as new… offers a name no look has, so its first press saves a copy; a taken name overwrites in two presses", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  const box = screen.getByRole("textbox", { name: "look name" });
  await expect.element(box).not.toBeInTheDocument(); // folded under the ▾
  const caret = screen.getByRole("button", { name: "save as new…" });
  await caret.click();
  await expect.element(caret).toHaveAttribute("aria-expanded", "true");
  await expect.element(box).toHaveValue("warm 2");
  // The form's button is secondary: save stays the header's one primary.
  await expect.element(screen.getByRole("button", { name: "save as new", exact: true })).toHaveAttribute("data-variant", "secondary");
  await screen.getByRole("switch", { name: /^include brightness \d+%$/ }).click();
  await screen.getByRole("button", { name: "save as new", exact: true }).click();
  expect(sent).toEqual([{ type: "save", name: "warm 2", fade: null, master: false }]);
  await box.fill("cool");
  await screen.getByRole("button", { name: "overwrite" }).click();
  expect(sent).toHaveLength(1);
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to overwrite" }).click();
  expect(sent.at(-1)).toEqual({ type: "save", name: "cool", fade: null, master: false });
});

test("a look's settings hold its own fade, its place in shuffle and delete, each acting on it at once", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  const fade = screen.getByRole("combobox", { name: "warm's own fade" });
  await fade.selectOptions("own fade: 5 s");
  expect(sent).toEqual([{ type: "fade", name: "warm", fade: 5 }]);
  await screen.getByRole("switch", { name: "warm in shuffle" }).click();
  expect(sent.at(-1)).toEqual({ type: "cycle", name: "warm", on: false });
  await screen.getByRole("button", { name: "delete" }).click();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to delete" }).click();
  expect(sent.at(-1)).toEqual({ type: "delete", name: "warm" });
  // The fade is stored alone: edits elsewhere never wait on it.
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  await fade.selectOptions("own fade: 2 s");
  expect(sent.at(-1)).toEqual({ type: "fade", name: "warm", fade: 2 });
});

test("a save and a delete are announced once the engine has made them, not when asked", async () => {
  const { screen, receive } = await saving();
  const said = () => document.querySelector(".sr-only[role=status]:not(.variety *)")?.textContent;
  await screen.getByRole("button", { name: "save as new", exact: true }).click();
  expect(said()).toBe("");
  const items = [...AURA.looks!.items, { name: "warm 2", cycle: true, fade: 2 }];
  receive(aura({ looks: { ...AURA.looks!, items, current: "warm 2", changed: false } }));
  await expect.poll(said).toBe("warm 2 saved");
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "delete" }).click();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to delete" }).click();
  receive(aura({ looks: { ...AURA.looks!, current: null } }));
  await expect.poll(said).toBe("warm 2 deleted");
  receive(aura({ looks: { ...AURA.looks!, current: null, made: "surprise 7", offered: "surprise 7" } }));
  await screen.getByRole("button", { name: "save", exact: true }).click();
  receive(aura({ looks: { ...AURA.looks!, current: "surprise 7", made: null } }));
  await expect.poll(said).toBe("surprise 7 saved");
});

test("save as new… closes once the engine has made its save, though the draft's ▾ that opened it is gone; a refusal keeps it", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  receive(aura({ looks: { ...AURA.looks!, current: null, made: "surprise 7", offered: "surprise 7" } }));
  const caret = screen.getByRole("button", { name: "save as new…" });
  await caret.click();
  const box = screen.getByRole("textbox", { name: "look name" });
  await box.fill("taken");
  box.element().focus();
  await userEvent.keyboard("{Enter}");
  receive(refused("save", "the looks file cannot be written"));
  await expect.element(screen.getByText("the looks file cannot be written")).toBeVisible();
  await expect.element(box).toBeVisible(); // refused: the form stays, to try again
  await box.fill("first");
  box.element().focus();
  await userEvent.keyboard("{Enter}");
  expect(sent.at(-1)).toEqual({ type: "save", name: "first", fade: null, master: true });
  await expect.element(box).toBeVisible(); // until the engine has made it
  const items = [...AURA.looks!.items, { name: "first", cycle: true, fade: 2 }];
  receive(aura({ looks: { ...AURA.looks!, items, current: "first", changed: false, made: null, offered: "first 2" } }));
  await expect.element(caret).not.toBeInTheDocument();
  await expect.element(box).not.toBeInTheDocument(); // hidden
  await expect.element(screen.getByRole("button", { name: "look settings" })).toHaveAttribute("aria-expanded", "false");
});

test("rename… sends the trimmed name and closes once the engine has made it, announcing it; a refusal keeps the form", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "rename…" }).click();
  const box = screen.getByRole("textbox", { name: "new name" });
  await expect.element(box).toHaveFocus();
  await expect.element(box).toHaveValue("warm");
  const go = screen.getByRole("button", { name: "rename", exact: true });
  await expect.element(go).toBeDisabled(); // unchanged
  await box.fill("  dusk  ");
  box.element().focus();
  await userEvent.keyboard("{Enter}");
  expect(sent).toEqual([{ type: "rename", name: "warm", to: "dusk" }]);
  receive(refused("rename", "a look is already named 'dusk'"));
  await expect.element(screen.getByText("a look is already named 'dusk'")).toBeVisible();
  await expect.element(box).toBeVisible(); // refused: the form stays, to try again
  box.element().focus();
  await userEvent.keyboard("{Enter}");
  expect(sent).toHaveLength(2);
  const items = AURA.looks!.items.map((i) => (i.name === "warm" ? { ...i, name: "dusk" } : i));
  receive(aura({ looks: { ...AURA.looks!, items, current: "dusk" } }));
  await expect.element(box).not.toBeInTheDocument();
  await expect.poll(() => document.querySelector(".sr-only[role=status]:not(.variety *)")?.textContent).toBe("renamed to dusk");
});

test("rename is off for an empty, unchanged or taken name", async () => {
  const { screen, sent } = await renderWired(<Editor />);
  const other = AURA.looks!.items.find((i) => i.name !== "warm")!.name;
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "rename…" }).click();
  const box = screen.getByRole("textbox", { name: "new name" });
  const go = screen.getByRole("button", { name: "rename", exact: true });
  await box.fill(other);
  await expect.element(screen.getByText("a look has that name")).toBeVisible();
  await expect.element(go).toBeDisabled();
  await box.fill("");
  await expect.element(go).toBeDisabled();
  await box.fill("Warm");
  await expect.element(go).toBeEnabled(); // names are case-sensitive
  expect(sent).toEqual([]);
});

test("rename is off while a cue plays the look, and a press says why at once, as an alert", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  receive(aura({ triggers: { ...AURA.triggers!, cues: { ...AURA.triggers!.cues, door: { look: "warm", hold: 20 } } } }));
  await screen.getByRole("button", { name: "look settings" }).click();
  const rename = screen.getByRole("button", { name: "rename…" });
  await expect.element(rename).toHaveAttribute("aria-disabled", "true");
  rename.element().focus();
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByRole("alert")).toHaveTextContent("door plays warm: change the looks file to rename it");
  await expect.element(screen.getByRole("textbox", { name: "new name" })).not.toBeInTheDocument();
  expect(sent).toEqual([]);
});

test("Esc closes rename…, focus back on what opened the settings", async () => {
  const { screen } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "rename…" }).click();
  await userEvent.keyboard("{Escape}");
  await expect.element(screen.getByRole("textbox", { name: "new name" })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "look settings" })).toHaveFocus();
});

test("Esc closes save as new… and the look's settings, focus back on what opened them", async () => {
  const { screen, receive } = await saving();
  screen.getByRole("textbox", { name: "look name" }).element().focus();
  await userEvent.keyboard("{Escape}");
  const dots = screen.getByRole("button", { name: "look settings" });
  await expect.element(screen.getByRole("textbox", { name: "look name" })).not.toBeInTheDocument(); // hidden
  await expect.element(dots).toHaveFocus(); // the settings opened it
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  const caret = screen.getByRole("button", { name: "save as new…" });
  await caret.click();
  screen.getByRole("textbox", { name: "look name" }).element().focus();
  await userEvent.keyboard("{Escape}");
  await expect.element(caret).toHaveAttribute("aria-expanded", "false");
  await expect.element(caret).toHaveFocus();
  await screen.getByRole("button", { name: "look settings" }).click();
  screen.getByRole("button", { name: "look settings" }).element().focus();
  await userEvent.keyboard("{Escape}");
  await expect.element(screen.getByRole("button", { name: "look settings" })).toHaveAttribute("aria-expanded", "false");
});

test("without a looks file, a look of layers says it cannot be saved", async () => {
  const { screen, receive } = await renderWired(<Editor />);
  const note = screen.getByText(/^not saved: this run can't keep looks/);
  await expect.element(note).not.toBeInTheDocument();
  const zoo = { id: "zoo", op: "zoo_test", label: "Zoo", in: [] };
  const layers = [{ id: "base", nodes: [zoo] }, { id: "top", nodes: [zoo] }];
  receive(aura({ looks: null, stack: { ...AURA.stack, layers, front: ["level"] } }));
  await expect.element(note).toBeVisible();
});

test("save as new… takes focus to the name box, selected, so a name typed at once goes in and never to the shortcuts", async () => {
  const { screen, sent, receive } = await renderWired(
    <>
      <Played />
      <Editor />
    </>,
  );
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  const saveAs = screen.getByRole("button", { name: "save as new…" });
  await saveAs.click();
  const box = screen.getByRole("textbox", { name: "look name" });
  await expect.element(box).toHaveFocus();
  await userEvent.keyboard("sunset");
  await expect.element(box).toHaveValue("sunset"); // the offered name was selected, so it is replaced
  saveAs.element().focus(); // its opener, while the form is open, is typing too
  await userEvent.keyboard("sbmk1");
  expect(sent).toEqual([]);
  await expect.element(screen.getByRole("button", { name: "again to black out" })).not.toBeInTheDocument();
});

test("delete is off while a cue plays the look, and a press says why at once, as an alert", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  receive(aura({ triggers: { ...AURA.triggers!, cues: { ...AURA.triggers!.cues, door: { look: "warm", hold: 20 } } } }));
  await screen.getByRole("button", { name: "look settings" }).click();
  const del = screen.getByRole("button", { name: "delete" });
  await expect.element(del).toHaveAttribute("aria-disabled", "true");
  del.element().focus(); // off for now, it keeps focus and says why when pressed
  await userEvent.keyboard("{Enter}");
  await expect.element(screen.getByRole("alert")).toHaveTextContent("door plays warm: change the looks file to delete it");
  await expect.element(screen.getByRole("button", { name: "again to delete" })).not.toBeInTheDocument();
  expect(sent).toEqual([]);
});

test("a refusal in the look's settings is an alert", async () => {
  const { screen, receive } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  receive(refused("cycle", "the looks file is read-only"));
  await expect.element(screen.getByRole("alert")).toHaveTextContent("the looks file is read-only");
});

test("the shuffle switch has a ? that says what shuffle is", async () => {
  const { screen } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "about shuffle" }).click();
  await expect.element(screen.getByText("while shuffle is on, the looks in it take turns at random")).toBeVisible();
});

test("shuffle's note shuts with the look settings: it keeps no Esc, and it does not come back unasked", async () => {
  const { screen } = await renderWired(<Editor />);
  const dots = screen.getByRole("button", { name: "look settings" });
  await dots.click();
  await screen.getByRole("button", { name: "about shuffle" }).click();
  const note = screen.getByText(/^while shuffle is on/);
  await expect.element(note).toBeVisible();
  let heard = 0;
  const hear = (e: KeyboardEvent) => {
    if (e.key === "Escape") heard += 1;
  };
  document.addEventListener("keydown", hear);
  try {
    await dots.click(); // shuts the settings, which stay in the page, hidden
    const ask = document.querySelector('[aria-label="about shuffle"]')!;
    await expect.poll(() => ask.getAttribute("aria-expanded")).toBe("false");
    await userEvent.keyboard("{Escape}");
    expect(heard).toBe(1); // the page has its Esc
    await dots.click();
    await expect.element(screen.getByRole("button", { name: "about shuffle" })).toBeVisible();
    await expect.element(note).not.toBeInTheDocument();
  } finally {
    document.removeEventListener("keydown", hear);
  }
});

test("while a recall waits for the running fade, the header says which look is next and the look waits, inert", async () => {
  const { screen, receive } = await renderWired(<Editor />);
  receive(aura({ looks: { ...AURA.looks!, fading: "warm", progress: 0.3, pending: "cool" } }));
  await expect.element(screen.getByText("cool next, when this fade ends")).toBeVisible();
  expect(document.querySelector(".look-block")?.hasAttribute("inert")).toBe(true);
  receive(aura({ looks: { ...AURA.looks!, current: "cool" } }));
  await expect.element(screen.getByText("cool next, when this fade ends")).not.toBeInTheDocument();
  expect(document.querySelector(".look-block")?.hasAttribute("inert")).toBe(false);
});

test("while a layer fails, save says so armed: the look saves as it fails", async () => {
  const { screen, receive } = await renderWired(
    <>
      <Editor />
      <ArmStatus />
    </>,
  );
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  receive({ type: "status", error: "boom", source: "render", path: "layers.base.zoo" });
  await screen.getByRole("button", { name: "save", exact: true }).click();
  await expect.element(screen.getByRole("button", { name: "again to save failing" })).toBeVisible();
  await expect.element(screen.getByRole("status").filter({ hasText: /^save failing\? .*failed; press again to save warm as it is$/ })).toBeInTheDocument();
});

test("a look name says what it needs as it is typed", async () => {
  const { screen } = await saving();
  const box = screen.getByRole("textbox", { name: "look name" });
  await box.fill("bad/name!");
  await expect.element(screen.getByText("letters, digits, space, _ or -")).toBeVisible();
  await expect.element(box).toHaveAttribute("aria-invalid", "true");
  await expect.element(screen.getByRole("button", { name: "save as new", exact: true })).toBeDisabled();
  await box.fill("good name");
  await expect.element(screen.getByText("letters, digits, space, _ or -")).not.toBeInTheDocument();
});

test("while a trigger holds a look, the header says so and what is under it waits, inert; the look shown is the held one", async () => {
  const { screen, receive } = await saving();
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, held: { trigger: "door", look: "cool", until: 9 } } }));
  await expect.element(screen.getByRole("heading", { name: "cool" })).toBeVisible();
  await expect.element(screen.getByText("door is playing cool: edit when it ends")).toBeVisible();
  expect(document.querySelector(".look-block")?.hasAttribute("inert")).toBe(true);
  await expect.element(screen.getByRole("button", { name: "save as new", exact: true })).toBeDisabled();
  receive(aura({ triggers: { ...AURA.triggers!, armed: true, held: null } }));
  await expect.element(screen.getByText("door is playing cool: edit when it ends")).not.toBeInTheDocument();
  expect(document.querySelector(".look-block")?.hasAttribute("inert")).toBe(false);
});

test("revert, in the look's settings while it is changed, recalls it with no fade in two presses", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  await expect.element(screen.getByRole("button", { name: "revert" })).not.toBeInTheDocument();
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  await expect.element(screen.getByRole("heading", { name: "warm (changed)" })).toBeVisible();
  await screen.getByRole("button", { name: "revert" }).click();
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to revert" }).click();
  expect(sent.at(-1)).toEqual({ type: "recall", name: "warm", fade: 0 });
});

test("a typed look name and the brightness switch outlive an engine restart; the box still follows a new current look", async () => {
  const { screen, receive } = await saving();
  const box = screen.getByRole("textbox", { name: "look name" });
  await box.fill("draftname");
  await screen.getByRole("switch", { name: /^include brightness \d+%$/ }).click();
  for (const msg of greeting()) receive(msg);
  await expect.element(box).toHaveValue("draftname");
  await expect.element(screen.getByRole("switch", { name: /^include brightness \d+%$/ })).not.toBeChecked();
  receive(hello());
  receive(aura({ looks: { ...AURA.looks!, current: "cool" } }));
  await expect.element(box).toHaveValue("cool 2");
});

test("a look refusal shows under the name until the name changes, and not in the status bar", async () => {
  const { screen, receive } = await saving(
    <>
      <StatusBar planNote={null} />
      <Editor />
    </>,
  );
  receive(refused("save", "warm is held by trigger door"));
  await expect.element(screen.getByText("warm is held by trigger door")).toBeVisible();
  await expect.element(screen.getByRole("textbox", { name: "look name" })).toHaveAttribute("aria-invalid", "true");
  expect(document.querySelector(".status-bar")?.textContent).toBe("");
  await screen.getByRole("textbox", { name: "look name" }).fill("warmer");
  await expect.element(screen.getByText("warm is held by trigger door")).not.toBeInTheDocument();
});

test("a render error says what the room shows and what to do; the others show as sent", async () => {
  const { screen, receive } = await renderWired(<StatusBar planNote={null} />);
  receive({ type: "status", error: "layers.base.zoo.render raised: ZeroDivisionError", source: "render", path: "layers.base.zoo" });
  const bar = screen.getByRole("status");
  await expect.element(screen.getByText("layers.base.zoo.render raised: ZeroDivisionError")).toHaveClass("status-detail");
  expect(document.querySelector(".status-bar")?.firstChild?.textContent).toBe(
    "The room is pulsing red: Zoo failed. Pick another look.",
  );
  const top = { id: "top", nodes: [{ id: "boom", op: "osc", label: "Oscillator", in: [] }] };
  receive(aura({ stack: { ...AURA.stack, layers: [...AURA.stack.layers, top] } }));
  receive({ type: "status", error: "layers.top.boom.render raised: ZeroDivisionError", source: "render", path: "layers.top.boom" });
  await expect.element(screen.getByText("layers.top.boom.render raised: ZeroDivisionError")).toHaveClass("status-detail");
  expect(document.querySelector(".status-bar")?.firstChild?.textContent).toBe(
    "Layer top (Oscillator) failed. Turn it off or remove it.",
  );
  receive({ type: "status", error: "reload failed, last-good room still running: ValueError", source: "reload", path: null });
  await expect.element(bar).toHaveTextContent("reload failed, last-good room still running: ValueError");
  expect(document.querySelector(".status-detail")).toBeNull();
});

test("the bar's lines: a refusal first, then the error, then the plan note", () => {
  const render = { text: "layers.base.zoo.render raised", source: "render", path: "layers.base.zoo" } as const;
  const refusal = { control: "recall", name: null, reason: "no look named x", issues: [], seq: 1 } as const;
  const lone = AURA.stack.layers;
  expect(barLines(refusal, render, lone, true, "plan")).toEqual(["no look named x"]);
  expect(barLines(null, render, lone, false, null)).toEqual([
    "The room is pulsing red: Zoo failed. Add a layer, then remove this one.", "layers.base.zoo.render raised",
  ]);
  expect(barLines(null, { ...render, path: "layers.base.gone" }, lone, false, null)[0]).toBe(
    "The room is pulsing red: layers.base.gone failed. Add a layer, then remove this one.",
  );
  expect(barLines(null, { ...render, source: "looks", path: null }, lone, true, "plan")).toEqual(["layers.base.zoo.render raised"]);
  expect(barLines(null, null, lone, true, "plan")).toEqual(["plan"]);
  expect(barLines(null, null, lone, true, null)).toEqual([]);
});

test("a failing layer among others is named, not said to turn the room red, and its row is what fixes it", () => {
  const layers = [{ id: "base", nodes: [{ id: "wave", op: "osc", label: "Oscillator", in: [] }] }, { id: "top", nodes: [] }];
  const failed = (path: string) => barLines(null, { text: `${path}.render raised`, source: "render", path }, layers, true, null)[0];
  expect(failed("layers.top.boom")).toBe("Layer top failed. Turn it off or remove it.");
  expect(failed("layers.base.wave")).toBe("Layer base (Oscillator) failed. Turn it off or remove it.");
});

test("what failed, in a few words: the phone bar's lead and the health panel's reason", () => {
  const layers = [{ id: "base", nodes: [{ id: "wave", op: "osc", label: "Oscillator", in: [] }] }, { id: "top", nodes: [] }];
  const render = (path: string) => ({ text: "raised", source: "render", path }) as const;
  expect(failedText(render("layers.base.wave"), layers)).toBe("base · Oscillator failed");
  expect(failedText(render("layers.base.wave"), layers.slice(0, 1))).toBe("Oscillator failed");
  expect(failedText(render("layers.top.boom"), layers)).toBe("top failed");
  expect(failedText({ text: "reload failed", source: "reload", path: null }, layers)).toBeNull();
  expect(failedText(null, layers)).toBeNull();
});

test("a refused control with no text of its own shows its reason in the status bar", async () => {
  const { screen, receive } = await renderWired(<StatusBar planNote={null} />);
  receive(refused("blackout", "no blackout for you"));
  await expect.element(screen.getByRole("status")).toHaveTextContent("no blackout for you");
  receive(refused("set", "no set for you", "level"));
  await expect.element(screen.getByRole("status")).toHaveTextContent("no blackout for you");
});

test("a refusal puts back what the control was waiting on", async () => {
  const { screen, receive } = await saving(
    <>
      <Editor />
      <Played />
    </>,
  );
  await screen.getByRole("textbox", { name: "look name" }).fill("warm");
  await screen.getByRole("button", { name: "overwrite" }).click();
  receive(refused("save", "no"));
  await expect.element(screen.getByRole("button", { name: "overwrite" })).toBeVisible();
  const master = screen.getByRole("slider", { name: "brightness" });
  master.element().focus();
  await userEvent.keyboard("{Home}");
  await expect.element(master).toHaveAttribute("aria-valuenow", "0");
  receive(refused("master", "no"));
  await expect.element(master).toHaveAttribute("aria-valuenow", "0.8");
});

test("the brightness steps by its − and +, within its max, and says where a run of steps left it", async () => {
  const { screen, sent, receive } = await renderWired(
    <>
      <Played />
      <StepStatus />
    </>,
  );
  await screen.getByRole("button", { name: "brightness down 5%" }).click();
  expect(sent.at(-1)).toEqual({ type: "master", value: 0.75 });
  receive(aura({ master: 0.75 }));
  receive(aura({ master: 0.97 }));
  await screen.getByRole("button", { name: "brightness up 5%" }).click();
  expect(sent.at(-1)).toEqual({ type: "master", value: 1 });
  await expect.element(screen.getByRole("status").filter({ hasText: /^brightness/ })).toHaveTextContent("brightness 100%");
});

test("over unsaved edits a look recalls in two presses, by tap or key, and a note under the looks says what the second does", async () => {
  const { screen, sent, receive } = await renderWired(<Played />);
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  const cool = screen.getByRole("button", { name: "cool" });
  await cool.click();
  expect(sent).toEqual([]);
  await expect.element(cool).toHaveAttribute("data-armed");
  await expect.element(screen.getByText("press cool again to drop the edits to warm")).toBeVisible();
  pastDoubleTap();
  await cool.click();
  expect(sent).toEqual([{ type: "recall", name: "cool", fade: null }]);
  await userEvent.keyboard("2");
  expect(sent).toHaveLength(1);
  await expect.element(screen.getByText("press warm again to drop its edits")).toBeVisible();
  pastDoubleTap();
  await userEvent.keyboard("2");
  expect(sent.at(-1)).toEqual({ type: "recall", name: "warm", fade: null });
  receive(aura({ looks: { ...AURA.looks!, changed: false } }));
  await expect.element(screen.getByText(/^press .* again to drop/)).not.toBeInTheDocument();
  await userEvent.keyboard("1");
  expect(sent.at(-1)).toEqual({ type: "recall", name: "cool", fade: null });
});

test("a mode's badge is not pressable; its ? says what it means under the top bar, until Esc or a second press", async () => {
  await page.viewport(1280, 800);
  const { screen, receive } = await renderWired(<App />);
  receive(aura({ triggers: { ...AURA.triggers!, armed: true } }));
  await expect.element(screen.getByRole("banner").getByText("cues on", { exact: true })).toBeVisible();
  expect(document.querySelector(".badge")?.closest("button")).toBeNull();
  const ask = screen.getByRole("button", { name: "about cues on" });
  await ask.click();
  // Its note, by the id its ? controls: the deck's ⋯ says the same, hidden.
  const note = () => document.getElementById(ask.element().getAttribute("aria-controls")!)!;
  await expect.poll(() => note().hidden).toBe(false);
  expect(note().textContent).toMatch(/^cues: a cue plays a look briefly/);
  await expect.element(ask).toHaveAttribute("aria-expanded", "true");
  expect(note().getBoundingClientRect().top).toBeGreaterThanOrEqual(document.querySelector(".top-bar")!.getBoundingClientRect().bottom); // under its row
  await userEvent.keyboard("{Escape}");
  await expect.poll(() => note().hidden).toBe(true);
  await expect.element(ask).toHaveAttribute("aria-expanded", "false");
  await ask.click();
  await expect.poll(() => note().hidden).toBe(false);
  await ask.click();
  await expect.poll(() => note().hidden).toBe(true);
  await page.viewport(414, 896);
});

test("the deck's note closes on Esc and on a press outside the deck", async () => {
  const { screen } = await renderWired(
    <>
      <Played />
      <button type="button">elsewhere</button>
    </>,
  );
  const about = screen.getByRole("button", { name: MORE });
  await about.click();
  await expect.element(screen.getByText(/room events/)).toBeVisible();
  await userEvent.keyboard("{Escape}");
  await expect.element(screen.getByText(/room events/)).not.toBeVisible();
  await about.click();
  await expect.element(screen.getByText(/room events/)).toBeVisible();
  await screen.getByRole("button", { name: "elsewhere" }).click();
  await expect.element(screen.getByText(/room events/)).not.toBeVisible();
});

test("a max has a ? that says what it is, in a note under the brightness, until Esc", async () => {
  const { screen, receive } = await renderWired(<Played />);
  await expect.element(screen.getByRole("button", { name: "about max" })).not.toBeInTheDocument(); // no max, nothing to explain
  receive(aura({ cap: 0.8 }));
  await expect.element(screen.getByText("max 80%")).toBeVisible();
  const ask = screen.getByRole("button", { name: "about max" });
  await ask.click();
  await expect.element(ask).toHaveAttribute("aria-expanded", "true");
  await expect.element(ask).toHaveAttribute("aria-controls", document.querySelector(".master .disclosure-note")!.id);
  await expect.element(screen.getByText(/the highest brightness allowed in this run/)).toBeVisible();
  ask.element().focus(); // WebKit focuses no button on a click
  await userEvent.keyboard("{Escape}");
  await expect.element(screen.getByText(/the highest brightness allowed in this run/)).not.toBeInTheDocument();
  await expect.element(ask).toHaveAttribute("aria-expanded", "false");
  await expect.element(ask).toHaveFocus();
});

test("at 360 px nothing slides the deck sideways; the ⋯'s sign ends the looks' row at the column's edge, as the brightness's steps do, and blackout has its own row", async () => {
  await page.viewport(360, 780);
  const { screen } = await renderWired(<Played />);
  const rows = document.querySelector<HTMLElement>(".deck-rows")!;
  await expect.element(screen.getByRole("button", { name: MORE })).toBeVisible();
  expect(rows.scrollWidth).toBeLessThanOrEqual(rows.clientWidth);
  const edge = Math.round(rows.getBoundingClientRect().right - parseFloat(getComputedStyle(rows).paddingRight));
  const [looks, more, steps] = [".looks", ".deck .more", ".master .joined"].map((part) => document.querySelector(part)!.getBoundingClientRect());
  expect(Math.round(more!.left)).toBeGreaterThanOrEqual(Math.round(looks!.right));
  // Its icon reaches 2 past the edge, the room its 16-unit grid keeps round the glyph, so the dots' ink ends on it.
  expect(Math.round(document.querySelector(".deck .more .icon")!.getBoundingClientRect().right)).toBe(edge + 2);
  expect(Math.round(steps!.right)).toBe(edge);
  // The brightness's slider takes the row the steps leave it; blackout is the row under it, the whole width.
  const slider = document.querySelector(".master [data-part=control]")!.getBoundingClientRect();
  const blackout = screen.getByRole("button", { name: "blackout" }).element().getBoundingClientRect();
  expect(slider.width).toBeGreaterThan(150);
  expect(blackout.top).toBeGreaterThan(steps!.bottom);
  expect(Math.round(blackout.width)).toBe(Math.round(rows.clientWidth - parseFloat(getComputedStyle(rows).paddingLeft) - parseFloat(getComputedStyle(rows).paddingRight)));
  await page.viewport(414, 896);
});

test("an armed button is red whatever its own style, and arming one moves nothing in the deck", async () => {
  const { screen, receive } = await renderWired(<Played />);
  receive(aura({ looks: { ...AURA.looks!, changed: true } }));
  const surprise = screen.getByRole("group", { name: "make a look" }).getByRole("button").first();
  const like = screen.getByRole("button", { name: "vary this" });
  await expect.element(surprise).toBeVisible();
  const before = [surprise.element().getBoundingClientRect().width, like.element().getBoundingClientRect().left];
  await surprise.click();
  await expect.element(surprise).toHaveAttribute("data-armed");
  expect(getComputedStyle(surprise.element()).backgroundColor).toBe("rgb(185, 28, 28)");
  expect([surprise.element().getBoundingClientRect().width, like.element().getBoundingClientRect().left]).toEqual(before);
  const blackout = screen.getByRole("button", { name: "blackout" });
  const width = blackout.element().getBoundingClientRect().width;
  await blackout.click();
  expect(screen.getByRole("button", { name: "again to black out" }).element().getBoundingClientRect().width).toBe(width);
});

/** Twelve looks, in file order. */
const twelve = Array.from({ length: 12 }, (_, i) => ({ name: `look ${i + 1}`, cycle: true, fade: 2 }));

test("the looks are tiles under a quiet caption, the first nine; the make actions are a row of their own, outside the tiles", async () => {
  await page.viewport(1280, 800);
  const { screen, receive } = await renderWired(<Played />);
  receive(aura({ looks: { ...AURA.looks!, items: twelve, favorites: twelve.slice(0, 9).map((l) => l.name), current: "look 2" } }));
  const tiles = screen.getByRole("toolbar", { name: "looks" });
  await expect.element(tiles).toBeVisible();
  const names = [...tiles.element().querySelectorAll("button")].map((b) => b.getAttribute("aria-label"));
  expect(names).toEqual(twelve.slice(0, 9).map((l) => l.name)); // the tiles' row holds tiles alone
  expect(tiles.element().querySelectorAll(".tile")).toHaveLength(9);
  // The make actions are secondary buttons with signs, in their own named group, never in the tiles' row.
  const make = screen.getByRole("group", { name: "make a look" });
  for (const name of ["surprise me", "vary this"]) {
    const button = make.getByRole("button", { name });
    await expect.element(button).toHaveAttribute("data-variant", "secondary");
    expect(button.element().querySelector(".icon")).not.toBeNull();
    expect(tiles.element().contains(button.element())).toBe(false);
  }
  expect(make.element().closest("[role=toolbar]")).toBeNull();
  // Their row is 12 below the tiles'.
  const gap = make.element().getBoundingClientRect().top - tiles.element().closest(".looks-row")!.getBoundingClientRect().bottom;
  expect(Math.round(gap)).toBe(12);
  await page.viewport(414, 896);
});

test("keys 1–9 play the first nine looks in file order; a tenth has no key", async () => {
  const { sent, receive } = await renderWired(<Played />);
  receive(aura({ looks: { ...AURA.looks!, items: twelve, favorites: twelve.slice(0, 9).map((l) => l.name), current: "look 1" } }));
  await expect.poll(() => document.querySelectorAll(".looks .tile").length).toBe(9);
  await userEvent.keyboard("9");
  expect(sent.at(-1)).toEqual({ type: "recall", name: "look 9", fade: null });
  await userEvent.keyboard("3");
  expect(sent.at(-1)).toEqual({ type: "recall", name: "look 3", fade: null });
  expect(document.querySelector('[aria-keyshortcuts="9"]')?.getAttribute("aria-label")).toBe("look 9");
});

test("past nine looks, all N › lists every look in the slot, the first nine with their keys; a row plays its look, and ✕ closes it", async () => {
  await page.viewport(1280, 800);
  const { screen, sent, receive } = await renderWired(<App />);
  const all = screen.getByRole("button", { name: "all 12 looks" });
  await expect.element(all).not.toBeInTheDocument(); // two looks: nothing more to list
  receive(aura({ looks: { ...AURA.looks!, items: twelve, favorites: twelve.slice(0, 9).map((l) => l.name), current: "look 1" } }));
  await expect.element(all).toHaveTextContent("all 12 ›");
  await expect.element(all).toHaveAttribute("data-variant", "tertiary");
  await all.click();
  const list = screen.getByRole("region", { name: "looks" });
  await expect.element(list).toBeVisible();
  await expect.element(all).toHaveAttribute("aria-expanded", "true");
  const rows = list.getByRole("listitem");
  expect(rows.elements()).toHaveLength(12);
  const keys = [...list.element().querySelectorAll("kbd")].map((k) => k.textContent);
  expect(keys).toEqual(["1", "2", "3", "4", "5", "6", "7", "8", "9"]);
  await expect.element(list.getByRole("button", { name: "look 1, favorite" })).toHaveAttribute("aria-pressed", "true"); // playing
  await list.getByRole("button", { name: "look 11" }).click();
  expect(sent.at(-1)).toEqual({ type: "recall", name: "look 11", fade: null });
  await expect.element(list).toBeVisible(); // it stays, for the next
  await screen.getByRole("button", { name: "close looks" }).click();
  await expect.element(list).not.toBeInTheDocument();
  await expect.element(all).toHaveAttribute("aria-expanded", "false");
  await page.viewport(414, 896);
});

/** The deck's looks with `names` as saved looks and `favorites` the favorites. */
const withLooks = (names: readonly string[], favorites: readonly string[], current: string | null = null) =>
  aura({ looks: { ...AURA.looks!, items: names.map((name) => ({ name, cycle: true, fade: 2 })), favorites, current } });

const NAMES = ["surprise 10", "Tide", "surprise 2", "amber", "Zinc", "surprise 1"];

test("the tiles are the favorites in natural, case-blind alphabetical order, and keys 1–9 follow it", async () => {
  const { sent, receive } = await renderWired(<Played />);
  receive(withLooks(NAMES, ["surprise 10", "Tide", "surprise 2", "amber"]));
  const tiles = () => [...document.querySelectorAll(".looks .tile")].map((b) => b.getAttribute("aria-label"));
  await expect.poll(tiles).toEqual(["amber", "surprise 2", "surprise 10", "Tide"]);
  await userEvent.keyboard("3");
  expect(sent.at(-1)).toEqual({ type: "recall", name: "surprise 10", fade: null });
  await userEvent.keyboard("5");
  expect(sent).toHaveLength(1); // a fourth tile has no fifth key
});

test("all N › shows while a look is not a favorite, and the row says when there are no favorites", async () => {
  const { screen, receive } = await renderWired(<App />);
  receive(withLooks(["a", "b"], ["a", "b"]));
  await expect.element(screen.getByRole("button", { name: "a", exact: true })).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "all 2 looks" })).not.toBeInTheDocument();
  receive(withLooks(["a", "b"], ["a"]));
  await expect.element(screen.getByRole("button", { name: "all 2 looks" })).toBeVisible();
  receive(withLooks(["a", "b"], []));
  await expect.element(screen.getByText(/No favorites/)).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "all 2 looks" })).toBeVisible();
});

test("the favorite switch sends its message, and is off at 20 favorites for a look that is not one", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  const fav = screen.getByRole("switch", { name: "warm a favorite" });
  await expect.element(fav).toBeChecked();
  await fav.click();
  expect(sent.at(-1)).toEqual({ type: "favorite", name: "warm", on: false });
  const many = Array.from({ length: 21 }, (_, i) => `look ${i + 1}`);
  receive(withLooks(many, many.slice(0, 20), "look 21"));
  const full = screen.getByRole("switch", { name: "look 21 a favorite" });
  await expect.element(full).toBeDisabled();
  await expect.element(screen.getByText("20 looks are favorites already; unfavorite one first")).toBeVisible();
  receive(withLooks(many, many.slice(0, 20), "look 20"));
  await expect.element(screen.getByRole("switch", { name: "look 20 a favorite" })).toBeEnabled();
});

test("the all-looks list is alphabetical, marks favorites and searches by substring", async () => {
  await page.viewport(1280, 800);
  const { screen, sent, receive } = await renderWired(<App />);
  receive(withLooks(NAMES, ["Zinc"]));
  await screen.getByRole("button", { name: "all 6 looks" }).click();
  const list = screen.getByRole("region", { name: "looks" });
  const rows = () => [...list.element().querySelectorAll("li .tile")].map((b) => b.getAttribute("aria-label"));
  expect(rows()).toEqual(["amber", "surprise 1", "surprise 2", "surprise 10", "Tide", "Zinc, favorite"]);
  const box = screen.getByRole("combobox", { name: "search looks" });
  expect(document.activeElement).toBe(box.element()); // opens with the box focused, so typing filters at once
  await box.fill("SURP");
  await expect.poll(rows).toEqual(["surprise 1", "surprise 2", "surprise 10"]);
  await box.fill("zzz");
  await expect.element(screen.getByText("no look matches")).toBeVisible();
  await box.fill("surprise 2");
  expect(rows()).toEqual(["surprise 2"]);
  await box.fill("sur");
  const active = () => box.element().getAttribute("aria-activedescendant");
  const id = () => document.getElementById(active()!)?.textContent;
  await expect.poll(id).toContain("surprise 1");
  box.element().focus();
  await userEvent.keyboard("{ArrowDown}{ArrowDown}");
  await expect.poll(id).toContain("surprise 10");
  await userEvent.keyboard("{ArrowUp}");
  await expect.poll(id).toContain("surprise 2");
  await userEvent.keyboard("{Enter}");
  expect(sent.at(-1)).toEqual({ type: "recall", name: "surprise 2", fade: null });
  await expect.element(list).toBeVisible(); // playing leaves the list open
  // Esc clears the box first, and a second one closes the list.
  await userEvent.keyboard("{Escape}");
  await expect.element(box).toHaveValue("");
  expect(rows()).toHaveLength(6);
  await expect.element(list).toBeVisible();
  await userEvent.keyboard("{Escape}");
  await expect.element(list).not.toBeInTheDocument();
  await page.viewport(414, 896);
});

test("rename… closes when another look becomes current, so it cannot rename that one", async () => {
  const { screen, sent, receive } = await renderWired(<Editor />);
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "rename…" }).click();
  const box = screen.getByRole("textbox", { name: "new name" });
  await box.fill("dusk");
  const other = AURA.looks!.items.find((i) => i.name !== "warm")!.name;
  receive(aura({ looks: { ...AURA.looks!, current: other } }));
  await expect.element(box).not.toBeInTheDocument();
  expect(sent).toEqual([]);
});

test("the all-looks list scrolls to the highlight when it moves, not on unrelated aura messages", async () => {
  await page.viewport(1280, 800);
  const calls: string[] = [];
  const real = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function (this: Element) {
    calls.push(this.id);
  };
  try {
    const { screen, receive } = await renderWired(<App />);
    const state = { ...AURA.looks!, items: twelve, favorites: twelve.slice(0, 9).map((l) => l.name), current: "look 1" };
    receive(aura({ looks: state }));
    await screen.getByRole("button", { name: "all 12 looks" }).click();
    await expect.poll(() => calls.length).toBeGreaterThan(0);
    const before = calls.length;
    receive(aura({ looks: { ...state } }));
    receive(aura({ looks: { ...state, changed: true } }));
    await new Promise((r) => setTimeout(r, 50));
    expect(calls).toHaveLength(before);
    await userEvent.keyboard("{ArrowDown}");
    await expect.poll(() => calls.length).toBe(before + 1);
  } finally {
    Element.prototype.scrollIntoView = real;
    await page.viewport(414, 896);
  }
});

test("shuffle is a switch, its row says what it is doing at a glance, its settings act at once, and on it starts as it last did", async () => {
  const { screen, sent, receive, store } = await renderWired(<Played />);
  const looks = AURA.looks!;
  const toggle = screen.getByRole("switch", { name: "shuffle" });
  // The file waits 5 min untouched, then plays each look 1 min.
  await expect.element(toggle).toBeChecked();
  act(() => store.receiveFrame({ t: 60, seq: 1, rgb: new Uint8Array(6) }, 0));
  const open = screen.getByRole("button", { name: "shuffle settings: every 1 min" });
  await expect.element(open).toHaveTextContent("1 min ·starts in4:00");
  await expect.element(open).toHaveAccessibleDescription(/^1 min ·\s*starts in\s*4:00$/);
  await open.click();
  await expect.element(open).toHaveAttribute("aria-expanded", "true");
  await expect.element(screen.getByText("after a touch, shuffle waits 5 min")).toBeVisible();
  await screen.getByRole("combobox", { name: "how long each look plays" }).selectOptions("120");
  expect(sent.at(-1)).toEqual({ type: "idle_cycle", each: 120 });
  await userEvent.keyboard("{Escape}");
  await expect.element(open).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  expect(sent.at(-1)).toEqual({ type: "idle_cycle", idle: null });
  // Off, the row says the lights stay; on again, it waits as it did.
  receive(aura({ looks: { ...looks, idle: null, next: null } }));
  await expect.element(toggle).not.toBeChecked();
  await expect.element(screen.getByText("stays on this look")).toBeVisible();
  expect(document.querySelector(".shuffle-open")).toBeNull();
  await toggle.click();
  expect(sent.at(-1)).toEqual({ type: "idle_cycle", idle: 300 });
  // Right away, a look's turn counts down.
  receive(aura({ looks: { ...looks, idle: 60, next: 90, cycling: true } }));
  await expect.element(screen.getByRole("button", { name: "shuffle settings: every 1 min" })).toHaveTextContent("1 min ·next in0:30");
  await screen.getByRole("button", { name: "shuffle settings: every 1 min" }).click();
  await screen.getByRole("combobox", { name: "when shuffle starts" }).selectOptions("600");
  expect(sent.at(-1)).toEqual({ type: "idle_cycle", idle: 600 });
  // A run that keeps shuffle off (a Gallery visit) offers none.
  receive(aura({ looks: { ...looks, idle: null, next: null, idle_off: true } }));
  await expect.element(toggle).not.toBeInTheDocument();
});

test("on a phone down to 360 px shuffle's row is one line that keeps the turn and the countdown", async () => {
  for (const width of [390, 360]) {
    await page.viewport(width, 844);
    const { screen, store, receive } = await renderWired(<Played />);
    receive(aura({ looks: { ...AURA.looks!, idle: 1800, dwell: [600, 600], next: 1860 } }));
    act(() => store.receiveFrame({ t: 60, seq: 1, rgb: new Uint8Array(6) }, 0));
    const row = document.querySelector(".shuffle-group > .bool-control")!.getBoundingClientRect();
    expect(row.height).toBeLessThanOrEqual(24);
    const each = document.querySelector(".shuffle-each")!;
    expect(each.scrollWidth).toBeLessThanOrEqual(each.clientWidth + 1); // "10 min ·" whole
    const parts = [screen.getByText("shuffle", { exact: true }), screen.getByRole("button", { name: /^shuffle settings/ }), screen.getByRole("switch", { name: "shuffle" })].map((l) => l.element().getBoundingClientRect());
    expect(parts[0]!.right).toBeLessThan(parts[1]!.left);
    expect(parts[1]!.right).toBeLessThanOrEqual(parts[2]!.left);
    expect(parts[2]!.right).toBeLessThanOrEqual(row.right + 1);
    await screen.unmount();
  }
  await page.viewport(414, 896);
});

import { expect, test } from "vitest";
import { page, userEvent } from "vitest/browser";
import { MAX_LOOKS, type LooksState } from "../../src/domain/aura/looks";
import { Deck } from "../../src/ui/deck/Deck";
import { LookPanel } from "../../src/ui/deck/LookPanel";
import { StatusBar } from "../../src/ui/status/StatusBar";
import { TopBar } from "../../src/ui/status/TopBar";
import { refused, AURA } from "../fixtures/messages";
import { pastDoubleTap, renderWired } from "./harness";

const looks = (patch: Partial<LooksState>) => ({ type: "aura" as const, ...AURA, looks: { ...AURA.looks!, ...patch } });

function Played() {
  return (
    <>
      <TopBar healthOpen={false} onHealth={() => {}} onHelp={() => {}} />
      <StatusBar planNote={null} />
      <LookPanel />
      <Deck />
    </>
  );
}

/** Off for now: it keeps focus and says why when pressed, so it is aria-disabled, not disabled. */
const OFF = ["aria-disabled", "true"] as const;
const ON = "aria-disabled";

test("surprise asks the engine, and the two wait, the one pressed busy and focused, until it answers", async () => {
  const { screen, sent, answer, receive } = await renderWired(<Played />);
  const surprise = screen.getByRole("group", { name: "make a look" }).getByRole("button").first(); // its name changes while busy
  const like = screen.getByRole("button", { name: "vary this" });
  surprise.element().focus();
  await userEvent.keyboard("{Enter}");
  expect(sent).toEqual([{ type: "surprise", seed: null }]);
  await expect.element(surprise).toHaveAttribute("data-busy");
  await expect.element(surprise).toHaveAccessibleName("making…");
  await expect.element(surprise).toHaveAttribute("aria-busy", "true");
  await expect.element(surprise).toHaveFocus();
  await expect.element(like).toHaveAttribute(...OFF);
  // The one pressed pulses, never amber, which is for the room; the other is off for now, in text-disabled.
  expect(getComputedStyle(surprise.element()).animationName).toBe("busy");
  expect(getComputedStyle(surprise.element()).borderTopColor).toBe("rgba(237, 237, 240, 0.18)"); // its quiet edge
  expect(getComputedStyle(like.element()).color).toBe("rgb(95, 95, 98)");
  await userEvent.keyboard("s");
  (like.element() as HTMLElement).click();
  expect(sent).toHaveLength(1); // no second send while the first is made
  receive(looks({ current: null, made: "surprise 1", offered: "surprise 1" }));
  await answer();
  await expect.element(surprise).not.toHaveAttribute("data-busy");
  await expect.element(surprise).toHaveFocus();
  await expect.element(screen.getByRole("status").filter({ hasText: "now playing surprise 1" })).toBeInTheDocument();
  await expect.element(like).not.toHaveAttribute(ON);
  await like.click();
  expect(sent.at(-1)).toEqual({ type: "vary", strength: null, seed: null });
});

test("each make is named by its label and announced, though a save would count past a saved look to one name", async () => {
  const { screen, receive, answer } = await renderWired(<Played />);
  const said = () => document.querySelector(".variety [role=status]")?.textContent;
  // "surprise 2" to "4" saved in an earlier run: this run's makes count from 1, its saves past them.
  for (const [made, offered] of [["surprise 1", "surprise 1"], ["surprise 2", "surprise 5"], ["surprise 3", "surprise 5"]] as const) {
    await screen.getByRole("button", { name: "surprise me" }).click();
    receive(looks({ current: null, made, offered }));
    await answer();
    await expect.poll(said).toBe(`now playing ${made}`);
    await expect.element(screen.getByRole("heading", { name: `${made} , draft` })).toBeVisible();
  }
  await expect.element(screen.getByRole("button", { name: "save", exact: true })).toHaveAttribute("title", "keep surprise 5");
});

test("over unsaved edits, surprise me and vary this take two presses, by tap or key", async () => {
  const { screen, sent, receive, answer } = await renderWired(<Played />);
  receive(looks({ changed: true }));
  await screen.getByRole("button", { name: "surprise me" }).click();
  expect(sent).toEqual([]);
  pastDoubleTap();
  await screen.getByRole("button", { name: "again to drop" }).click();
  expect(sent).toEqual([{ type: "surprise", seed: null }]);
  await answer();
  await userEvent.keyboard("m");
  expect(sent).toHaveLength(1);
  pastDoubleTap();
  await userEvent.keyboard("m");
  expect(sent.at(-1)).toEqual({ type: "vary", strength: null, seed: null });
});

test("over a made look's edits, surprise me, vary this and a look take two presses; the note follows the one armed", async () => {
  const { screen, sent, receive } = await renderWired(<Played />);
  receive(looks({ current: null, made: "surprise 7", offered: "surprise 7", changed: true }));
  await expect.element(screen.getByRole("heading", { name: "surprise 7 , draft" })).toBeVisible(); // a draft, never "changed"
  await screen.getByRole("button", { name: "cool" }).click();
  const chip = screen.getByText("press cool again to drop surprise 7 and its edits");
  await expect.element(chip).toBeVisible();
  await screen.getByRole("button", { name: "surprise me" }).click();
  await expect.element(chip).not.toBeInTheDocument();
  await expect.element(screen.getByText("press surprise me again to drop surprise 7 and its edits")).toBeVisible();
  await screen.getByRole("button", { name: "vary this" }).click();
  await expect.element(screen.getByRole("button", { name: "again to vary" })).toBeVisible();
  await expect.element(screen.getByText("press vary this again to vary what plays; save first to keep these edits in surprise 7")).toBeVisible();
  expect(sent).toEqual([]);
  await userEvent.keyboard("{Escape}");
  await expect.element(screen.getByText(/press vary this again/)).not.toBeInTheDocument();
});

test("a press that arms one and disarms another shows the new one's note, whichever comes first on the page", async () => {
  const { screen, receive } = await renderWired(<Played />);
  receive(looks({ changed: true }));
  const made = screen.getByRole("group", { name: "make a look" }).getByRole("button");
  const [surprise, like] = [made.first(), made.last()];
  await surprise.click();
  await screen.getByRole("button", { name: "cool" }).click(); // the looks' row comes before the made looks'
  await expect.element(screen.getByText("press cool again to drop the edits to warm")).toBeVisible();
  await screen.getByRole("button", { name: /^warm/ }).click(); // the tile before it in its row
  await expect.element(screen.getByText("press warm again to drop its edits")).toBeVisible();
  await like.click();
  await surprise.click(); // the button before it in its row
  await expect.element(screen.getByText("press surprise me again to drop the edits to warm")).toBeVisible();
});

test("a mode's note goes with its badge: it keeps no Esc, and it does not come back unasked", async () => {
  const { screen, receive } = await renderWired(<Played />);
  const arm = (armed: boolean) => receive({ type: "aura", ...AURA, triggers: { ...AURA.triggers!, armed } });
  const ask = screen.getByRole("button", { name: "about cues on" });
  // The badge's note, by the id its ? controls: the deck's ⋯ says the same, hidden.
  let id = "";
  const note = () => (id ? document.getElementById(id) : null);
  let heard = 0;
  const hear = (e: KeyboardEvent) => {
    if (e.key === "Escape") heard += 1;
  };
  document.addEventListener("keydown", hear);
  try {
    arm(true);
    await ask.click();
    id = ask.element().getAttribute("aria-controls")!;
    await expect.poll(() => note()?.hidden).toBe(false);
    expect(note()?.textContent).toMatch(/^cues: a cue plays a look briefly/);
    arm(false);
    await expect.element(ask).not.toBeInTheDocument();
    expect(note()).toBeNull(); // it went with its badge
    await userEvent.keyboard("{Escape}");
    expect(heard).toBe(1); // the page has its Esc
    arm(true);
    await expect.element(ask).toHaveAttribute("aria-expanded", "false");
    id = ask.element().getAttribute("aria-controls")!;
    expect(note()?.hidden).toBe(true);
  } finally {
    document.removeEventListener("keydown", hear);
  }
});

test("a refused make goes to the status bar and frees the buttons", async () => {
  const { screen, receive, answer } = await renderWired(<Played />);
  await screen.getByRole("button", { name: "vary this" }).click();
  const reason = "no change of the running look made from seed 4 passed the content gate; try another seed";
  receive(refused("vary", reason));
  await answer();
  await expect.element(screen.getByText(reason)).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "vary this" })).not.toHaveAttribute(ON);
});

test("vary this needs a look playing; a press on it then says what to press first", async () => {
  const { screen, sent, receive } = await renderWired(<Played />);
  const like = screen.getByRole("button", { name: "vary this" });
  receive(looks({ current: null }));
  await expect.element(like).toHaveAttribute(...OFF);
  (like.element() as HTMLElement).click();
  expect(sent).toEqual([]);
  await expect.element(screen.getByText("vary this needs a look playing: press one, or surprise me, first")).toBeVisible();
  receive(looks({ current: null, made: "surprise 7" }));
  await expect.element(like).not.toHaveAttribute(ON);
  await expect.element(screen.getByText(/needs a look playing/)).not.toBeInTheDocument();
});

test("save, in the look's header while a made look plays, keeps it in one press under the name the header shows", async () => {
  const { screen, sent, receive, answer } = await renderWired(<Played />);
  const save = screen.getByRole("button", { name: "save", exact: true });
  await expect.element(save).not.toBeInTheDocument(); // warm plays as saved
  receive(looks({ current: null, made: "surprise 7", offered: "surprise 7" }));
  await expect.element(screen.getByRole("heading", { name: "surprise 7 , draft" })).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "look settings" })).not.toBeInTheDocument(); // a draft has no settings yet
  await screen.getByRole("button", { name: "save as new…" }).click();
  const box = screen.getByRole("textbox", { name: "look name" });
  await expect.element(box).toHaveValue("");
  await expect.element(box).toHaveAttribute("placeholder", "surprise 7");
  await expect.element(screen.getByRole("button", { name: "save as new", exact: true })).toBeEnabled();
  await expect.element(box).toHaveFocus(); // so a name typed at once goes in, never to the shortcuts
  document.querySelector<HTMLElement>(".look-title")!.focus();
  await userEvent.keyboard("k"); // k presses save
  expect(sent).toEqual([{ type: "save", name: null, fade: null, master: null }]); // the engine names it as it offers
  await expect.element(save).toHaveAttribute("data-busy");
  await userEvent.keyboard("k");
  expect(sent).toHaveLength(1); // busy: no second save
  receive(looks({ items: [...AURA.looks!.items, { name: "surprise 7", cycle: false, fade: 2 }], current: "surprise 7", made: null, offered: "surprise 8" }));
  await answer();
  await expect.element(screen.getByRole("button", { name: "surprise 7" })).toHaveAttribute("aria-pressed", "true");
  await expect.element(save).not.toBeInTheDocument(); // saved: nothing to save
  await expect.element(screen.getByRole("heading", { name: "surprise 7", exact: true })).toBeVisible();
  await expect.element(screen.getByRole("textbox", { name: "look name" })).not.toBeInTheDocument(); // its form went with its ▾
  await screen.getByRole("button", { name: "look settings" }).click();
  await screen.getByRole("button", { name: "save as new…" }).click();
  await expect.element(screen.getByRole("textbox", { name: "look name" })).toHaveValue("surprise 8"); // a copy's, now that it is saved
});

test("a save as new of a draft with no name typed keeps it under its offered name, with the brightness switch's choice", async () => {
  const { screen, sent, receive } = await renderWired(<Played />);
  receive(looks({ current: null, made: "surprise 7", offered: "surprise 7" }));
  await screen.getByRole("button", { name: "save as new…" }).click();
  await screen.getByRole("switch", { name: /^include brightness/ }).click();
  await screen.getByRole("button", { name: "save as new", exact: true }).click();
  expect(sent).toEqual([{ type: "save", name: null, fade: null, master: false }]);
});

test("k with nothing to save says why under the header, and a cue's hold takes save away", async () => {
  const { screen, receive } = await renderWired(<Played />);
  document.querySelector<HTMLElement>(".look-title")!.focus();
  await userEvent.keyboard("k");
  await expect.element(screen.getByText("warm is saved")).toBeVisible();
  await userEvent.keyboard("k");
  await expect.element(screen.getByText("warm is saved")).not.toBeInTheDocument();
  const held = { ...AURA.triggers!, held: { trigger: "door", look: "cool", until: 9 } };
  receive({ type: "aura", ...AURA, looks: { ...AURA.looks!, current: null, made: "surprise 7", offered: null }, triggers: held });
  await expect.element(screen.getByText("door is playing cool: edit when it ends")).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "save", exact: true })).not.toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "vary this" })).not.toHaveAttribute(ON);
  document.querySelector<HTMLElement>(".look-title")!.focus();
  await userEvent.keyboard("k");
  await expect.element(screen.getByRole("status").filter({ hasText: "door is playing cool: save when it ends" })).toBeVisible();
  receive(looks({ current: null, made: "surprise 7", offered: "surprise 7" }));
  await expect.element(screen.getByRole("button", { name: "save", exact: true })).toBeVisible();
});

test("a refused save of the header shows its reason under the header", async () => {
  const { screen, receive } = await renderWired(<Played />);
  receive(looks({ current: null, made: "surprise 7", offered: "surprise 7" }));
  await screen.getByRole("button", { name: "save", exact: true }).click();
  receive(refused("save", "there are already 64 looks; delete one first"));
  await expect.element(screen.getByRole("status").filter({ hasText: "there are already 64 looks; delete one first" })).toBeVisible();
});

test("with 64 looks saved, a draft's save is off, in text-disabled, and a press or k says why, sending nothing", async () => {
  const { screen, sent, receive } = await renderWired(<Played />);
  const items = Array.from({ length: MAX_LOOKS }, (_, i) => ({ name: `look ${i + 1}`, cycle: true, fade: 2 }));
  receive(looks({ items, current: null, made: "surprise 7", offered: "surprise 7" }));
  const save = screen.getByRole("button", { name: "save", exact: true });
  await expect.element(save).toHaveAttribute(...OFF);
  expect(getComputedStyle(save.element()).color).toBe("rgb(95, 95, 98)");
  (save.element() as HTMLElement).click();
  const why = screen.getByRole("status").filter({ hasText: "there are already 64 looks; delete one first" });
  await expect.element(why).toBeVisible();
  document.querySelector<HTMLElement>(".look-title")!.focus();
  await userEvent.keyboard("k");
  await expect.element(why).not.toBeInTheDocument();
  await userEvent.keyboard("k");
  await expect.element(why).toBeVisible();
  expect(sent).toEqual([]);
  receive(looks({ items: items.slice(1), current: null, made: "surprise 7", offered: "surprise 7" })); // one deleted
  await expect.element(save).not.toHaveAttribute(ON);
  await expect.element(why).not.toBeInTheDocument();
});

test("on a phone down to 360 px the two share one line under the looks", async () => {
  for (const width of [390, 360]) {
    await page.viewport(width, 844);
    const { screen } = await renderWired(<Played />);
    const tops = ["surprise me", "vary this"].map(
      (name) => screen.getByRole("button", { name }).element().getBoundingClientRect(),
    );
    expect(new Set(tops.map((r) => Math.round(r.top))).size).toBe(1);
    const row = document.querySelector(".made-row")!.getBoundingClientRect();
    expect(Math.max(...tops.map((r) => r.right))).toBeLessThanOrEqual(row.right + 1);
    const saved = screen.getByRole("button", { name: /^warm/ }).element().getBoundingClientRect();
    expect(tops[0]!.top).toBeGreaterThan(saved.bottom - 1);
    screen.unmount();
  }
  await page.viewport(414, 896);
});

test("the deck's ⋯ holds the rare controls and says what the marks shown now mean, nothing more", async () => {
  const { screen, receive } = await renderWired(<Played />);
  receive(looks({ changed: true }));
  const more = screen.getByRole("button", { name: "more: cues, fade and what these do" });
  await more.click();
  await expect.element(more).toHaveAttribute("aria-expanded", "true");
  await expect.element(screen.getByRole("button", { name: "cues on" })).toBeVisible();
  await expect.element(screen.getByText("in shuffle", { exact: true })).toBeVisible(); // after its ↻; no cue holds a look, and "changed" is the header's
  expect(document.querySelector(".deck-more .cyc .icon")?.getAttribute("data-icon")).toBe("cycle");
  await expect.element(screen.getByText(/^cues: a cue plays a look briefly, then comes back; room events \(buttons, sensors\) fire them$/)).toBeVisible();
  expect(screen.getByText(/^surprise me: /).query()).toBeNull(); // each button says what it does by its title
  expect(screen.getByText(/^max: /).query()).toBeNull(); // the max's own ? says what it is
});

test("on a phone the look's header names a long name whole, on more lines, giving way first to save and the ⋯; the top bar names no look", async () => {
  await page.viewport(390, 844);
  const { receive } = await renderWired(<Played />);
  const text = () => document.querySelector<HTMLElement>(".look-name-text")!;
  const line = text().getBoundingClientRect().height; // "warm", on one line
  const name = "midnight harbour lanterns drift";
  receive(looks({ current: null, made: name, offered: name }));
  await expect.poll(() => document.querySelector(".look-head .split-button")).not.toBeNull();
  const head = document.querySelector(".look-head")!.getBoundingClientRect();
  const split = document.querySelector(".look-head .split-button")!.getBoundingClientRect();
  expect(split.right).toBeLessThanOrEqual(head.right);
  expect(text().textContent).toBe(name);
  expect(text().scrollWidth).toBeLessThanOrEqual(text().clientWidth); // never cut short
  expect(text().getBoundingClientRect().height).toBeGreaterThan(line * 1.5);
  expect(document.querySelector(".top-bar")!.textContent).not.toContain(name);
  await page.viewport(414, 896);
});

test("at 360 px the top bar holds every mode and the health word without sliding sideways", async () => {
  await page.viewport(360, 780);
  const { receive } = await renderWired(<Played />);
  receive({ type: "aura", ...AURA, blackout: true, looks: { ...AURA.looks!, cycling: true }, triggers: { ...AURA.triggers!, armed: true } });
  await expect.poll(() => document.querySelectorAll(".top-bar .badge").length).toBeGreaterThan(0);
  const bar = document.querySelector<HTMLElement>(".top-bar")!;
  expect(bar.scrollWidth).toBeLessThanOrEqual(bar.clientWidth);
  expect(getComputedStyle(document.querySelector(".health-chip > .t-value")!).textOverflow).toBe("ellipsis");
  await page.viewport(414, 896);
});

import { useState } from "react";
import { expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { Badge } from "../../src/design/Badge";
import { Button, IconButton, ToggleButton } from "../../src/design/Button";
import { DisclosureButton, DisclosureNote, useDisclosure } from "../../src/design/Disclosure";
import { Icon, ICON_NAMES } from "../../src/design/Icon";
import { ArmStatus } from "../../src/design/press";
import { Tile } from "../../src/design/Tile";
import { pastDoubleTap, renderWired } from "./harness";

// The colours the components draw in, as the browser reports them (theme.css).
const ACCENT = "rgb(217, 154, 43)";
const ON_ACCENT = "rgb(11, 11, 14)";
const BORDER_STRONG = "rgb(123, 123, 126)";
const BORDER_CONTROL = "rgba(237, 237, 240, 0.18)";
const DANGER_FG = "rgb(248, 113, 113)";
const DANGER_FILL = "rgb(185, 28, 28)";
const TEXT_1 = "rgb(237, 237, 240)";
const DISABLED = "rgb(95, 95, 98)";

const style = (el: Element) => getComputedStyle(el);

test("a button's rank shows in its style, never its size: primary solid amber, secondary a quiet edge, tertiary a word", async () => {
  const { screen } = await renderWired(
    <div className="row">
      <Button variant="primary" onPress={() => {}}>
        save
      </Button>
      <Button onPress={() => {}}>surprise</Button>
      <Button variant="tertiary" onPress={() => {}}>
        revert
      </Button>
      <Button variant="tertiary" tone="danger" onPress={() => {}}>
        delete
      </Button>
    </div>,
  );
  const [save, surprise, revert, del] = ["save", "surprise", "revert", "delete"].map((name) => screen.getByRole("button", { name }).element());
  expect([style(save!).backgroundColor, style(save!).color, style(save!).fontWeight]).toEqual([ACCENT, ON_ACCENT, "600"]);
  expect([style(surprise!).borderTopColor, style(surprise!).backgroundColor]).toEqual([BORDER_CONTROL, "rgba(0, 0, 0, 0)"]);
  expect([style(revert!).borderTopColor, style(revert!).color]).toEqual(["rgba(0, 0, 0, 0)", TEXT_1]);
  expect(style(del!).color).toBe(DANGER_FG);
  const heights = new Set([save, surprise, revert, del].map((el) => el!.getBoundingClientRect().height));
  expect(heights.size).toBe(1);
});

test("a confirm takes two presses: the first fills it red and says what the second does, in place, moving nothing", async () => {
  const fire = vi.fn();
  const { screen } = await renderWired(
    <>
      <Button tone="danger" confirm="again to black out" onPress={fire}>
        blackout
      </Button>
      <ArmStatus />
    </>,
  );
  const button = screen.getByRole("button", { name: "blackout" });
  const width = button.element().getBoundingClientRect().width;
  await button.click();
  expect(fire).not.toHaveBeenCalled();
  const armed = screen.getByRole("button", { name: "again to black out" });
  await expect.element(armed).toHaveAttribute("data-armed");
  expect(style(armed.element()).backgroundColor).toBe(DANGER_FILL);
  expect(armed.element().getBoundingClientRect().width).toBe(width);
  await expect.element(screen.getByRole("status")).toHaveTextContent("press again to black out");
  pastDoubleTap();
  await armed.click();
  expect(fire).toHaveBeenCalledTimes(1);
  await expect.element(screen.getByRole("button", { name: "blackout" })).not.toHaveAttribute("data-armed");
});

test("a confirm that is not needed now acts at once, and keeps its width for when it is", async () => {
  const fire = vi.fn();
  function Page() {
    const [two, setTwo] = useState(false);
    return (
      <>
        <Button confirm="again to drop" twoPress={two} onPress={fire}>
          surprise
        </Button>
        <button type="button" onClick={() => setTwo(true)}>
          edit
        </button>
      </>
    );
  }
  const { screen } = await renderWired(<Page />);
  const button = screen.getByRole("button", { name: "surprise" });
  const width = button.element().getBoundingClientRect().width;
  await button.click();
  expect(fire).toHaveBeenCalledTimes(1);
  await screen.getByRole("button", { name: "edit" }).click();
  await button.click();
  expect(fire).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "again to drop" }).element().getBoundingClientRect().width).toBe(width);
});

test("busy, a button pulses, says so, and ignores presses", async () => {
  const fire = vi.fn();
  const { screen } = await renderWired(
    <Button busy onPress={fire}>
      making…
    </Button>,
  );
  const button = screen.getByRole("button", { name: "making…" });
  await expect.element(button).toHaveAttribute("aria-busy", "true");
  expect(style(button.element()).animationName).toBe("busy");
  await button.click();
  expect(fire).not.toHaveBeenCalled();
});

test("off with a reason, a button keeps focus, and a press says why in its note instead of acting", async () => {
  const fire = vi.fn();
  function Page() {
    const why = useDisclosure();
    const [full, setFull] = useState(true);
    return (
      <>
        <Button reason={full ? "a look has at most 16 layers" : null} note={why} onPress={fire}>
          + layer
        </Button>
        <button type="button" onClick={() => setFull(false)}>
          remove one
        </button>
        <DisclosureNote disclosure={why} live />
      </>
    );
  }
  const { screen } = await renderWired(<Page />);
  const add = screen.getByRole("button", { name: "+ layer" });
  await expect.element(add).toHaveAttribute("aria-disabled", "true");
  expect(add.element().hasAttribute("disabled")).toBe(false);
  expect(style(add.element()).color).toBe(DISABLED);
  add.element().focus();
  await userEvent.keyboard("{Enter}");
  expect(fire).not.toHaveBeenCalled();
  await expect.element(add).toHaveFocus();
  const note = screen.getByRole("status");
  await expect.element(note).toHaveTextContent("a look has at most 16 layers");
  await expect.element(add).toHaveAccessibleDescription("a look has at most 16 layers");
  await screen.getByRole("button", { name: "remove one" }).click();
  await expect.element(screen.getByText("a look has at most 16 layers")).not.toBeInTheDocument(); // the reason went, and its note with it
  await add.click();
  expect(fire).toHaveBeenCalledTimes(1);
});

test("a key presses a button while it can be pressed", async () => {
  const fire = vi.fn();
  const { screen } = await renderWired(
    <Button shortcut={{ hotkey: "s", label: "surprise" }} onPress={fire}>
      surprise
    </Button>,
  );
  await expect.element(screen.getByRole("button", { name: "surprise" })).toBeVisible();
  await userEvent.keyboard("s");
  expect(fire).toHaveBeenCalledTimes(1);
});

test("an icon button is a square named by its label; its sign is hidden from assistive tech", async () => {
  const fire = vi.fn();
  const { screen } = await renderWired(<IconButton icon="close" label="close health" onPress={fire} />);
  const close = screen.getByRole("button", { name: "close health" });
  const box = close.element().getBoundingClientRect();
  expect(box.width).toBe(box.height);
  expect(close.element().querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
  await close.click();
  expect(fire).toHaveBeenCalledTimes(1);
});

test("a toggle says its state; on is the selected fill and weight 600, never amber unless it arms what the room answers", async () => {
  function Page() {
    const [layout, setLayout] = useState(false);
    const [armed, setArmed] = useState(false);
    return (
      <>
        <ToggleButton pressed={layout} onPressedChange={setLayout}>
          layout
        </ToggleButton>
        <ToggleButton tone="accent" pressed={armed} onPressedChange={setArmed} confirmOff="again to disarm">
          arm cues
        </ToggleButton>
      </>
    );
  }
  const { screen } = await renderWired(<Page />);
  const layout = screen.getByRole("button", { name: "layout" });
  await expect.element(layout).toHaveAttribute("aria-pressed", "false");
  await layout.click();
  await expect.element(layout).toHaveAttribute("aria-pressed", "true");
  expect([style(layout.element()).backgroundColor, style(layout.element()).fontWeight]).toEqual(["rgba(237, 237, 240, 0.12)", "600"]);
  expect(style(layout.element()).borderTopColor).toBe(BORDER_STRONG);
  const arm = screen.getByRole("button", { name: "arm cues" });
  await arm.click(); // on in one press
  await expect.element(arm).toHaveAttribute("aria-pressed", "true");
  expect([style(arm.element()).backgroundColor, style(arm.element()).borderTopColor]).toEqual(["rgba(217, 154, 43, 0.16)", ACCENT]);
  await arm.click(); // off in two
  const confirming = screen.getByRole("button", { name: "again to disarm" });
  await expect.element(confirming).toHaveAttribute("aria-pressed", "true");
  pastDoubleTap();
  await confirming.click();
  await expect.element(screen.getByRole("button", { name: "arm cues" })).toHaveAttribute("aria-pressed", "false");
});

test("a tile is a thing, not an action: raised, no edge; live is amber with a ●, and going live moves nothing", async () => {
  function Page() {
    const [live, setLive] = useState("warm");
    return (
      <div className="row">
        {["warm", "cool"].map((name) => (
          <Tile key={name} name={name} live={live === name} aria-pressed={live === name} onPress={() => setLive(name)} />
        ))}
      </div>
    );
  }
  const { screen } = await renderWired(<Page />);
  const [warm, cool] = ["warm", "cool"].map((name) => screen.getByRole("button", { name }));
  expect(warm!.element().hasAttribute("data-variant")).toBe(false);
  expect(style(cool!.element()).backgroundColor).toBe("rgb(33, 33, 36)"); // raised
  expect(style(cool!.element()).borderTopColor).toBe("rgb(33, 33, 36)"); // no edge of its own
  expect(style(warm!.element()).fontWeight).toBe("600");
  const dot = (tile: Element) => tile.querySelector('[data-icon="dot"]')!;
  expect([style(dot(warm!.element())).visibility, style(dot(cool!.element())).visibility]).toEqual(["visible", "hidden"]);
  const boxes = () => [warm, cool].map((t) => `${t!.element().getBoundingClientRect().left},${t!.element().getBoundingClientRect().width}`);
  const before = boxes();
  await cool!.click();
  await expect.element(cool!).toHaveAttribute("aria-pressed", "true");
  expect(style(cool!.element()).fontWeight).toBe("600");
  expect(boxes()).toEqual(before);
});

test("a tile a cue holds has an amber edge; a picked one the selected fill, never amber", async () => {
  const { screen } = await renderWired(
    <>
      <Tile name="dusk" held onPress={() => {}} />
      <Tile name="zoo" selected onPress={() => {}} />
    </>,
  );
  expect(style(screen.getByRole("button", { name: "dusk" }).element()).borderTopColor).toBe(ACCENT);
  const zoo = screen.getByRole("button", { name: "zoo" }).element();
  expect(style(zoo).borderTopColor).not.toBe(ACCENT);
  expect(style(zoo).backgroundImage).toContain("0.12");
});

test("a badge is a word in caps on the raised surface, never pressable", async () => {
  const { screen } = await renderWired(
    <Badge icon="cycle" tone="danger">
      idle cycle
    </Badge>,
  );
  const word = screen.getByText("idle cycle");
  const badge = word.element().closest(".badge")!;
  expect(badge.closest("button, [role=button]")).toBeNull();
  expect([style(badge).textTransform, style(badge).backgroundColor]).toEqual(["uppercase", "rgb(33, 33, 36)"]);
  expect(badge.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
});

/** Two words, each with its "?" and a note under it, and a panel that closes on Esc. */
function Notes({ onPanelEsc }: { onPanelEsc(): void }) {
  const a = useDisclosure();
  const b = useDisclosure();
  return (
    <section
      onKeyDown={(e) => {
        if (e.key === "Escape") onPanelEsc();
      }}
    >
      <div className="row">
        layers <DisclosureButton disclosure={a} label="about layers" />
      </div>
      <DisclosureNote disclosure={a}>One picture; higher layers draw over lower ones</DisclosureNote>
      <div className="row">
        blend <DisclosureButton disclosure={b} label="about blend" />
      </div>
      <DisclosureNote disclosure={b}>How this layer mixes with the layers below</DisclosureNote>
    </section>
  );
}

test("a ? opens one line under its row, as an APG disclosure: one open on the page, Esc closes it and nothing else", async () => {
  const panelEsc = vi.fn();
  const { screen } = await renderWired(<Notes onPanelEsc={panelEsc} />);
  const layers = screen.getByRole("button", { name: "about layers" });
  const blend = screen.getByRole("button", { name: "about blend" });
  const layersNote = screen.getByText(/^One picture/);
  await expect.element(layers).toHaveAttribute("aria-expanded", "false");
  await layers.click();
  await expect.element(layers).toHaveAttribute("aria-expanded", "true");
  await expect.element(layers).toHaveAttribute("aria-controls", layersNote.element().id);
  await expect.element(layersNote).toBeVisible();
  // In the page's flow under its row, not over what follows.
  expect(layersNote.element().getBoundingClientRect().bottom).toBeLessThanOrEqual(blend.element().getBoundingClientRect().top);
  await blend.click(); // one open at a time
  await expect.element(layersNote).not.toBeInTheDocument();
  await expect.element(layers).toHaveAttribute("aria-expanded", "false");
  await expect.element(screen.getByText(/^How this layer mixes/)).toBeVisible();
  blend.element().focus();
  await userEvent.keyboard("{Escape}");
  await expect.element(blend).toHaveAttribute("aria-expanded", "false");
  await expect.element(blend).toHaveFocus();
  expect(panelEsc).not.toHaveBeenCalled(); // Esc closed the note alone
  await userEvent.keyboard("{Escape}");
  expect(panelEsc).toHaveBeenCalledTimes(1);
  await blend.click();
  await blend.click(); // a second press closes it
  await expect.element(blend).toHaveAttribute("aria-expanded", "false");
});

test("every icon is drawn on its 16-unit grid whatever the text's size, in the current colour, hidden from assistive tech", async () => {
  await renderWired(
    <p style={{ fontSize: 20, color: "rgb(1, 2, 3)" }}>
      {ICON_NAMES.map((name) => (
        <Icon key={name} name={name} />
      ))}
    </p>,
  );
  const icons = [...document.querySelectorAll("svg.icon")];
  expect(icons.map((el) => el.getAttribute("data-icon"))).toEqual([...ICON_NAMES]);
  for (const icon of icons) {
    expect(icon.getAttribute("aria-hidden")).toBe("true");
    expect(icon.querySelector("path")).not.toBeNull();
    const box = icon.getBoundingClientRect();
    expect([box.width, box.height]).toEqual([16, 16]);
  }
  const stroked = document.querySelector('[data-icon="close"] path')!;
  const filled = document.querySelector('[data-icon="dot"] path.fill')!;
  expect(style(stroked).stroke).toBe("rgb(1, 2, 3)");
  expect(style(filled).fill).toBe("rgb(1, 2, 3)");
});

test("focus is a neutral outline, never amber", async () => {
  // A text box shows its focus in every browser; a button's comes from the same rule.
  const { screen } = await renderWired(<input aria-label="name" />);
  const box = screen.getByRole("textbox", { name: "name" });
  (box.element() as HTMLElement).focus();
  await expect.element(box).toHaveFocus();
  expect([style(box.element()).outlineColor, style(box.element()).outlineStyle, style(box.element()).outlineWidth]).toEqual([TEXT_1, "solid", "2px"]);
});

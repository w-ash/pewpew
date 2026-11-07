import { expect, test } from "vitest";
import {
  argParts, blendsAbout, brings, fits, newLayer, newText, offReason, patternLabels, SHELVES, shelve, shortText, showsBlack, sourceLabels, summaryText, type Card,
} from "../../src/domain/stack/catalog";
import { first } from "../fixtures/messages";

const { cards, blends } = first("catalog");
const [wave, kaleid] = cards as [Card, Card];
const op = (sig: string): Card => ({ ...kaleid, sig });

const BELOW = { py: "below().hue(90)", json: { out: "hue", nodes: { below: { op: "below" }, hue: { op: "hue", in: ["below"] } } }, dims: [1, 2, 3] };

test("a card goes on one shelf: a pattern's, an op that can act on the layers below on theirs, else its op's by what it does", () => {
  const names = (cs: readonly Card[]) => [...shelve(cs)].map(([shelf, held]) => [shelf, held.map((h) => `${h.card.name}/${h.at}`)]);
  expect(names([wave])[0]).toEqual(["patterns", ["wave/0"]]);
  expect(["source", "coord", "color", "state", "combine", "modulate"].map((sig) => names([op(sig)]).find(([, held]) => held?.length)?.[0])).toEqual([
    "sources", "space", "color", "trails and glow", "combine two patterns", "combine two patterns",
  ]);
  expect(SHELVES.slice(0, 3)).toEqual(["patterns", "sources", "effects on the layers below"]); // what runs as it is, first
  const hue: Card = { ...kaleid, name: "hue", sig: "color", examples: [kaleid.examples[0]!, BELOW] };
  expect(names([hue]).filter(([, held]) => held?.length)).toEqual([["effects on the layers below", ["hue/1"]]]);
  // Plumbing that means something only inside a program is no card.
  const plumbing = ["below", "prev", "pattern"].map((name): Card => ({ ...kaleid, name, sig: "source" }));
  expect(names(plumbing).filter(([, held]) => held?.length)).toEqual([]);
  expect(SHELVES[0]).toBe("patterns");
});

test("a card names the sources its example brings, none for a source or an effect on the layers below", () => {
  const sources = sourceLabels([{ ...kaleid, name: "osc", label: "Oscillator", sig: "source" }]);
  const folded: Card = { ...kaleid, examples: [{ ...kaleid.examples[0]!, json: { out: "k", nodes: { w: { op: "osc" }, k: { op: "kaleid", in: ["w"] } } } }, BELOW] };
  expect([brings(folded, 0, sources), brings(folded, 1, sources), brings({ ...folded, sig: "source" }, 0, sources)]).toEqual([["Oscillator"], [], []]);
  // What a press adds first leads the gist, in the words the sources' knobs use.
  expect([newText(["Oscillator"]), newText(["Noise", "Ripple"])]).toEqual(["new stripes", "new noise hills and ripple"]);
});

test("a card the map cannot run says what to use instead; a pattern runs on any map", () => {
  expect(offReason(kaleid, 1)).toBe("a strip has no plane to fold; use mirror along the strip");
  expect(offReason(kaleid, 0)).toBe(offReason(kaleid, 1)); // a point runs what a strip runs
  expect([offReason(kaleid, 2), offReason(kaleid, 3), offReason(wave, 0)]).toEqual([null, null, null]);
  expect(offReason({ ...kaleid, fix: "" }, 1)).toBe("needs a map of 2 or 3 dimensions");
});

test("a card whose op runs on the map but whose own example does not says so; its other examples that run stay", () => {
  // The pattern op runs on a strip; its own example folds it with kaleid, which does not.
  const folded = { ...kaleid.examples[0]!, dims: [2, 3] };
  const tinted = { ...kaleid.examples[0]!, dims: [1, 2, 3] };
  const pattern: Card = { ...kaleid, name: "pattern", dims: [1, 2, 3], fix: "", examples: [folded, tinted] };
  expect(offReason(pattern, 1)).toBe("its example needs a map of 2 or 3 dimensions");
  expect(offReason(pattern, 2)).toBeNull();
  expect([fits(folded, 1), fits(folded, 0), fits(folded, 3), fits(tinted, 0)]).toEqual([false, false, true, true]);
});

test("a summary keeps an arg's name apart, to set as a token", () => {
  const counted = { ...kaleid, summary: "Folds a pattern into mirrored wedges: `sides` of them." };
  expect(argParts(summaryText(counted))).toEqual(["Folds a pattern into mirrored wedges: ", "sides", " of them"]);
});

test("a card's gist is its summary up to the first colon or semicolon; its ? shows only when the rest says more", () => {
  expect(shortText(kaleid)).toBe("Folds a pattern into mirrored wedges about the center, as a kaleidoscope does");
  const more = { ...kaleid, summary: "Lets `mod` warp `in`: each point reads it moved; so one ripples another." };
  expect(shortText(more)).toBe("Lets `mod` warp `in`");
});

test("a new layer screens over the layers under it, unless it reads them", () => {
  const own = kaleid.examples[0]!;
  expect(newLayer(own)).toEqual({ ...own.json, blend: "screen", opacity: 0.7 });
  expect(newLayer(BELOW)).toBe(BELOW.json);
});

test("a blend's help leads with what the chosen mode does, and on the bottom layer when it shows black; the rest wait", () => {
  const { lead, more } = blendsAbout(blends, "screen", false);
  expect(lead).toBe("screen: Adds light without washing out to white");
  expect(more.split("\n")).toHaveLength(blends.length - 1);
  expect(more).not.toContain("screen:");
  expect(blendsAbout(blends, "multiply", true).lead.split("\n").at(-1)).toBe("Nothing is below this layer, so multiply shows black.");
  expect(blendsAbout(blends, "screen", true).lead.split("\n")).toHaveLength(1);
  expect([showsBlack(blends, "multiply"), showsBlack(blends, "screen"), showsBlack(blends, "nope")]).toEqual([true, false, false]);
});

test("a pattern goes by its card's label in lower case, its doc's title; one no card names, by its name", () => {
  const labels = patternLabels([{ ...wave, name: "colorplasma", label: "Color plasma" }, kaleid]);
  expect([...labels]).toEqual([["colorplasma", "color plasma"]]);
});

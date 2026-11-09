import { expect, test } from "vitest";
import { percent } from "../../src/params/format";
import {
  countdown, cycleText, eachItems, eachRequest, eachText, FADES, fadeSeconds, RIGHT_AWAY, rightAway, shuffleOn, shuffleStatus, shuffleSwitch, span, startItems, startRequest, findLook, holdReason, liveLook, lookStatus, MAX_LOOKS, nameHint, offSaved, saveOf, unsaved, varyReason, type LooksState,
} from "../../src/aura/looks";
import { param } from "../fixtures/describe";
import { capText, stepMaster } from "../../src/aura/master";
import { nowOf, type AuraState } from "../../src/aura/aura";
import { armable, cueText, lastText } from "../../src/aura/triggers";

const stack = { layers: [{ id: "base", nodes: [{ id: "osc", op: "osc", label: "Oscillator", in: [] }] }], signals: [], routes: [], front: [], dims: 1 } as const;
const aura = (patch: Partial<AuraState>): AuraState => ({
  stack, fading: false, progress: null, master: 1, cap: 1,
  blackout: false, looks: null, triggers: null, ...patch,
});
/** The looks: none current, made or waiting, idle cycle at its defaults, but for `patch`. */
const looksOf = (patch: Partial<LooksState>): LooksState => ({
  items: [], favorites: [], current: null, changed: false, fading: null, progress: null, pending: null, cycling: false, idle: 300, dwell: [60, 60],
  idle_off: false, next: null, made: null, offered: null, saved: null, ...patch,
});
/** A cue that holds look cool. */
const HELD = { armed: true, names: ["door"], cues: {}, held: { trigger: "door", look: "cool", until: 9 }, last: null };

test("look status", () => {
  const looks = looksOf({ items: [{ name: "warm", cycle: true, fade: 2 }], current: "warm", changed: true, fading: "cool", progress: 0.4, pending: "deep" });
  const held = { armed: true, names: ["door"], cues: {}, held: { trigger: "door", look: "warm", until: 12 }, last: null };
  expect(lookStatus(looks, held, "warm")).toEqual({ live: true, returnsTo: false, changed: false, fading: null, pending: false, held: true });
  expect(lookStatus(looks, null, "cool")).toMatchObject({ live: false, changed: false, fading: 0.4 });
  const other = { ...held, held: { ...held.held, look: "cool" } };
  expect(lookStatus(looks, other, "warm")).toMatchObject({ live: false, returnsTo: true });
  expect(lookStatus(looks, other, "cool")).toMatchObject({ live: true, held: true });
  expect(liveLook(looks, other)).toBe("cool");
  expect(liveLook(looks, null)).toBe("warm");
  expect(lookStatus(looks, null, "deep").pending).toBe(true);
  // A recall that waits replaces the edits: they are not marked, over the held look's layers least of all.
  expect(lookStatus({ ...looks, pending: null }, null, "warm").changed).toBe(true);
  expect(findLook(looks, " warm ")?.name).toBe("warm");
  expect(findLook(null, "warm")).toBeUndefined();
});

test("fades say what they choose", () => {
  expect(FADES.map((f) => f.label)).toEqual([
    "fade: as saved", "fade: instant", "fade: 0.5 s", "fade: 1 s", "fade: 2 s", "fade: 3 s", "fade: 5 s", "fade: 10 s", "fade: 30 s",
  ]);
  expect(fadeSeconds("stored")).toBeNull();
  expect(fadeSeconds("0.5")).toBe(0.5);
});

test("cues count down from engine time", () => {
  const held = { trigger: "door", look: "warm", until: 12 };
  expect(cueText("door", held, 9.2)).toBe("door · 3s");
  expect(cueText("door", held, 13)).toBe("door · 0s");
  expect(cueText("door", { ...held, until: null }, 0)).toBe("door · …");
  expect(cueText("bell", held, 0)).toBe("bell");
  expect(lastText({ name: "door", fired: true, reason: null, error: null })).toEqual({ text: "door fired", tick: false });
  expect(lastText({ name: "door", fired: true, reason: null, error: null }, true)).toEqual({ text: "door", tick: true }); // a phone's short line: the page draws ✓
  expect(lastText({ name: "door", fired: false, reason: "disarmed", error: null }, true)).toEqual({ text: "door: cues off", tick: false });
  expect(lastText({ name: "door", fired: false, reason: "cooldown", error: null }).text).toBe("door: cooldown");
  expect(lastText({ name: "door", fired: true, reason: null, error: "no looks file" })).toEqual({ text: "door fired, but no looks file", tick: false });
  expect(lastText(null)).toEqual({ text: "", tick: false });
  expect(armable(null)).toBe(false);
  expect(armable({ armed: true, names: [], cues: {}, held: null, last: null })).toBe(true);
  expect(armable({ armed: false, names: [], cues: {}, held: null, last: null })).toBe(false);
});

test("brightness and its max", () => {
  expect(percent(0.555)).toBe("56%");
  expect(capText(1)).toBe("");
  expect(capText(0.8)).toBe("max 80%");
  expect(stepMaster(0.6, 1, -1)).toBe(0.55);
  expect(stepMaster(0.78, 0.8, 1)).toBe(0.8);
  expect(stepMaster(0.02, 1, -1)).toBe(0);
});

test("the look's header names what plays: the live look, else a draft, else nothing", () => {
  const looks = looksOf({ current: "warm", offered: "warm 2" });
  const now = (patch: Partial<AuraState>) => nowOf(aura(patch));
  expect(now({ master: 0.6 })).toEqual({ name: "", changed: false, draft: false, master: "60%" }); // no looks file
  expect(now({ looks })).toMatchObject({ name: "warm", changed: false, draft: false });
  expect(now({ looks: { ...looks, changed: true } })).toMatchObject({ name: "warm", changed: true });
  expect(now({ looks, triggers: HELD })).toMatchObject({ name: "cool", changed: false });
  // A made look: a draft, never "changed".
  const made = { ...looks, current: null, made: "surprise 7", offered: "surprise 7", changed: true };
  expect(now({ looks: made })).toMatchObject({ name: "surprise 7", changed: false, draft: true });
  // A made look by its label, new for each make, even where a save counts past a saved name to another.
  expect(now({ looks: { ...made, made: "surprise 3", offered: "surprise 5" } }).name).toBe("surprise 3");
  expect(now({ looks: { ...made, made: "surprise 4", offered: "surprise 5" } }).name).toBe("surprise 4");
  expect(now({ looks: { ...looks, current: null, offered: "kept" } })).toMatchObject({ name: "kept", draft: true });
  expect(now({ looks: { ...looks, changed: true, pending: "cool" } })).toMatchObject({ name: "warm", changed: false });
});

test("the one save: into the changed look, a draft kept under its name, or nothing and why", () => {
  const looks = looksOf({ items: [{ name: "warm", cycle: true, fade: 2 }], current: "warm", offered: "warm 2" });
  expect(saveOf(looks, null)).toEqual({ kind: "none", why: "warm is saved" });
  expect(saveOf({ ...looks, changed: true }, null)).toEqual({ kind: "over", name: "warm" });
  expect(saveOf({ ...looks, current: null, made: "surprise 7", offered: "surprise 7" }, null)).toEqual({ kind: "draft", name: "surprise 7", full: null });
  expect(saveOf({ ...looks, current: null, offered: "kept" }, null)).toEqual({ kind: "draft", name: "kept", full: null });
  // A full looks file takes no new look: a draft's save is off and says why; a changed look still saves into itself.
  const items = Array.from({ length: MAX_LOOKS }, (_, i) => ({ name: `look ${i + 1}`, cycle: true, fade: 2 }));
  const full = "there are already 64 looks; delete one first";
  expect(saveOf({ ...looks, items, current: null, offered: "kept" }, null)).toEqual({ kind: "draft", name: "kept", full });
  expect(saveOf({ ...looks, items: items.slice(1), current: null, offered: "kept" }, null)).toEqual({ kind: "draft", name: "kept", full: null });
  expect(saveOf({ ...looks, items, changed: true }, null)).toEqual({ kind: "over", name: "warm" });
  expect(saveOf({ ...looks, changed: true, offered: null }, HELD)).toEqual({ kind: "none", why: "door is playing cool: save when it ends" });
  expect(saveOf({ ...looks, changed: true, pending: "cool" }, null)).toEqual({ kind: "none", why: "cool next, when this fade ends" });
});

test("shuffle says how long each look plays and when it starts, or that the lights stay on the look", () => {
  const looks = looksOf({ cycling: true, dwell: [40, 90] });
  expect(cycleText(looks)).toBe("shuffle: the looks in shuffle play at random, 40–90 s each; starts after 5 min untouched");
  expect(cycleText({ ...looks, idle: 120, dwell: [120, 120] })).toBe("shuffle: the looks in shuffle play at random, 2 min each; after a touch, the look plays its whole turn");
  expect(cycleText({ ...looks, idle: null })).toBe("shuffle is off: the lights stay on the look");
  expect([30, 60, 90, 120, 3600].map(span)).toEqual(["30 s", "1 min", "90 s", "2 min", "1 h"]);
  expect(eachText(looksOf({ dwell: [20, 45] }))).toBe("20–45 s");
});

test("shuffle is one switch: on, right away at the turn the file has; off, the lights stay", () => {
  const looks = looksOf({ idle: null, dwell: [120, 120] });
  expect(shuffleOn(looks)).toBe(false);
  expect(shuffleSwitch(looks, true)).toEqual({ type: "idle_cycle", idle: 120 });
  expect(shuffleSwitch(looksOf({}), false)).toEqual({ type: "idle_cycle", idle: null });
  // A turn shorter than the engine takes for a wait asks for the shortest wait.
  expect(shuffleSwitch(looksOf({ dwell: [0.5, 0.5] }), true)).toEqual({ type: "idle_cycle", idle: 1 });
  const now = looksOf({ idle: 60, dwell: [60, 60] });
  expect(rightAway(now) && !rightAway(looksOf({}))).toBe(true);
  // Right away stays right away when the turn changes; a wait stays as it is.
  expect(eachRequest(now, 300)).toEqual({ type: "idle_cycle", idle: 300, each: 300 });
  expect(eachRequest(looksOf({}), 300)).toEqual({ type: "idle_cycle", each: 300 });
  expect(startRequest(looksOf({}), RIGHT_AWAY)).toEqual({ type: "idle_cycle", idle: 60 });
  expect(startRequest(now, "600")).toEqual({ type: "idle_cycle", idle: 600 });
});

test("the turns and starts offered hold the file's own when it is none of them", () => {
  expect(eachItems(looksOf({})).value).toBe("60");
  expect(eachItems(looksOf({})).items.map((i) => i.label)).toEqual(["each look: 30 s", "each look: 1 min", "each look: 2 min", "each look: 5 min", "each look: 10 min", "each look: 30 min"]);
  const range = eachItems(looksOf({ dwell: [40, 90] }));
  expect([range.value, range.items[0]]).toEqual(["range", { value: "range", label: "each look: 40–90 s" }]);
  expect(eachItems(looksOf({ dwell: [45, 45] })).items.map((i) => i.value)).toEqual(["30", "45", "60", "120", "300", "600", "1800"]);
  const starts = startItems(looksOf({}));
  expect(starts.value).toBe("300");
  expect(starts.items.slice(0, 2)).toEqual([{ value: RIGHT_AWAY, label: "starts: right away" }, { value: "60", label: "starts: after 1 min untouched" }]);
  expect(startItems(looksOf({ idle: 60 })).value).toBe(RIGHT_AWAY);
  expect(startItems(looksOf({ idle: 450 })).items.map((i) => i.value)).toContain("450");
});

test("shuffle's line counts down to the next look, or says why it waits", () => {
  const items = [{ name: "warm", cycle: true, fade: 2 }];
  const waiting = looksOf({ items, current: "warm", next: 300 });
  expect(shuffleStatus(waiting, null, 36)).toBe("starts in 4:24");
  expect(shuffleStatus({ ...waiting, cycling: true, next: 400 }, null, 399.2)).toBe("next in 0:01");
  expect(shuffleStatus({ ...waiting, idle: 60, next: 90 }, null, 30)).toBe("next in 1:00");
  expect(shuffleStatus({ ...waiting, next: null, changed: true }, null, 0)).toBe("waits: save or revert to go on");
  expect(shuffleStatus({ ...waiting, next: null }, HELD, 0)).toBe("waits for door to end");
  expect(shuffleStatus({ ...waiting, next: null }, null, 0)).toBe("ended");
  expect(shuffleStatus({ ...waiting, items: [{ ...items[0]!, cycle: false }] }, null, 0)).toBe("no looks in shuffle: add one from its ⋯");
  expect(shuffleStatus({ ...waiting, idle: null }, null, 0)).toBe("");
  expect([countdown(0), countdown(59.2), countdown(3725)]).toEqual(["0:00", "1:00", "1:02:05"]);
});

test("vary this needs a look playing and says what to press first; a save waits while a cue holds a look", () => {
  const looks = looksOf({ items: [{ name: "warm", cycle: false, fade: 2 }] });
  expect(varyReason(looks)).toBe("vary this needs a look playing: press one, or surprise me, first");
  expect(varyReason({ ...looks, items: [] })).toBe("vary this needs a look playing: press surprise me first");
  expect(varyReason({ ...looks, made: "surprise 7" })).toBeNull();
  expect(varyReason({ ...looks, current: "warm" })).toBeNull();
  expect(holdReason(HELD, "save")).toBe("door is playing cool: save when it ends");
  expect(holdReason(null, "save")).toBeNull();
});

test("unsaved edits are a current look changed; a look name is what the engine takes", () => {
  const looks = looksOf({ current: "warm", changed: true });
  expect([unsaved(looks), unsaved({ ...looks, changed: false }), unsaved({ ...looks, current: null }), unsaved({ ...looks, pending: "cool" }), unsaved(null)]).toEqual([
    true, false, false, false, false,
  ]);
  expect(["warm", "late look_2", "", "a".repeat(32)].map(nameHint)).toEqual([null, null, null, null]);
  expect(["bad/name!", " lead", "a".repeat(33)].map(nameHint)).toEqual(Array(3).fill("letters, digits, space, _ or -"));
});

test("a part of the look is off saved when a knob in it moved, or a knob under it came or went", () => {
  const level = { ...param("zoo_test", "level"), name: "layers.top.zoo.level" };
  const bands = { ...param("zoo_test", "bands"), name: "layers.top.zoo.bands" };
  const saved = { "layers.top.zoo.level": 0.5, "layers.top.zoo.bands": 2 };
  const at = (values: Record<string, unknown>) => (p: { name: string }) => values[p.name] as never;
  expect(offSaved([level, bands], at(saved), saved, "layers.top.")).toBe(false);
  expect(offSaved([level, bands], at({ ...saved, "layers.top.zoo.level": 0.6 }), saved)).toBe(true);
  expect(offSaved([level], at(saved), saved, "layers.top.")).toBe(true); // bands went
  expect(offSaved([level], at(saved), saved)).toBe(false); // without a prefix, only the knobs given count
  expect(offSaved([level, bands], at(saved), { "layers.top.zoo.level": 0.5 }, "layers.top.")).toBe(true); // bands came
});

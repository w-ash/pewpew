import { expect, test } from "vitest";
import {
  chainSaysMore, contextOf, depthOf, depthSign, frontFirst, isMix, isPattern, isSignal, layerOf, mixAddress, movedBy, moveTo, nodeAt, nodeOrder, ownerOf,
  pageCase, panelOf, pickedFront, routesInto, runs, sectionOf, signalKind, summaryOf, type SignalItem,
} from "../../src/stack/stack";
import catalog from "../../../tests/goldens/catalog.json";
import { param } from "../fixtures/describe";

const layers = [
  { id: "base", nodes: [{ id: "wash", op: "pattern", label: "wash", in: [] }] },
  { id: "top", nodes: [{ id: "sparkle", op: "pattern", label: "Sparkle", in: [] }] },
];
const knob = (layer: string, node: string, group = "") => ({ layer, node, group });
const SWING = [-1, 1] as const, LEVEL = [0, 1] as const;

test("an address names its layer and node, and the node's label", () => {
  expect(layerOf("layers.top.sparkle")).toBe("top");
  expect(layerOf("signals.lfo")).toBeNull();
  expect(nodeAt("layers.top.sparkle", layers)?.label).toBe("Sparkle");
  expect(nodeAt("layers.top.wash", layers)).toBeNull();
  expect(nodeAt("layers.gone.wash", layers)).toBeNull();
});

test("a section names its node, signal or group first, then its kind and what it reads; a layer's nodes go along its wiring", () => {
  const program = {
    id: "fx",
    nodes: [
      { id: "osc", op: "osc", label: "Oscillator", in: [] },
      { id: "osc2", op: "osc", label: "Oscillator", in: [] },
      { id: "fold", op: "kaleid", label: "Kaleidoscope", in: ["osc2"] },
      { id: "warp", op: "modulate", label: "Ripple", in: ["fold", "osc"] },
    ],
  };
  const all = [...layers, program];
  const signals = [
    { id: "breath", op: "lfo", label: "LFO", in: [], range: SWING }, { id: "hiss", op: "band", label: "Audio follower", in: [], range: LEVEL },
    { id: "kick", op: "beat", label: "Beat", in: [], range: LEVEL }, { id: "splash", op: "env", label: "Envelope", in: ["kick"], range: LEVEL },
    { id: "osc", op: "walk", label: "Random", in: [], range: SWING },
  ];
  const title = (p: ReturnType<typeof knob>, s = signals) => sectionOf(p, all, s)?.title;
  expect(title(knob("base", "wash", "Low"))).toBe("Low");
  expect(nodeOrder(program).map((n) => n.id)).toEqual(["osc2", "fold", "osc", "warp"]); // an extra input just before what reads it
  expect(title(knob("fx", "fold", "Low"))).toBe("fold · Kaleidoscope"); // reads the node before it
  expect(title(knob("fx", "warp"), [])).toBe("warp · Ripple ← fold, osc");
  expect(title(knob("fx", "warp"))).toBe("warp · Ripple ← fold, oscillator ‘osc’"); // a signal shares the name: say which
  expect(sectionOf(knob("fx", "warp"), all, signals)).toMatchObject({ name: "warp", kind: "Ripple", at: 3 });
  expect([title(knob("fx", "osc"), []), title(knob("fx", "osc2"))]).toEqual(["osc · Oscillator", "osc2 · Oscillator"]);
  expect([title(knob("", "breath")), title(knob("", "hiss")), title(knob("", "splash"))]).toEqual([
    "breath · LFO", "hiss · audio follower", "splash · envelope on kick", // the engine's labels: an acronym keeps its capitals
  ]);
  expect(title(knob("", "", "Motion"))).toBe("Motion"); // a record that names no layer keeps its group
  expect(sectionOf(knob("base", "wash"), all)).toBeNull();
});

test("a look that lists no front shows the knobs the engine would pick: routed, then each layer's first, never an opacity", () => {
  const named = (name: string, layer: string, node: string) => ({ name, layer, node, group: "" });
  const params = [named("layers.base.wash.speed", "base", "wash"), named("layers.top.sparkle.rate", "top", "sparkle"), named("layers.top.opacity", "top", "")];
  const routes = [{ source: "breath", path: "layers.top.sparkle.rate", depth: 1 }];
  const stack = { layers, signals: [], routes, front: [], dims: 2 as const };
  expect(panelOf(params, stack, null).front.map((p) => p.name)).toEqual(["layers.top.sparkle.rate", "layers.base.wash.speed"]);
  expect(pickedFront({ ...stack, routes: [] }, params)).toEqual(["layers.base.wash.speed", "layers.top.sparkle.rate"]);
  // A lone pattern shows its knobs under it: nothing in front.
  expect(pickedFront({ ...stack, layers: layers.slice(0, 1) }, params)).toEqual([]);
});

test("the panel shows the front knobs and the signals', then a lone layer's knobs, its mix only off its defaults, or the picked layer's", () => {
  const named = (name: string, layer: string, node: string, group = "") => ({ name, layer, node, group });
  const params = [
    named("layers.base.wash.speed", "base", "wash"), named("layers.base.opacity", "base", ""),
    named("layers.top.sparkle.rate", "top", "sparkle", "Glints"), named("layers.top.opacity", "top", ""),
    named("signals.breath.rate", "", "breath"), named("level", "", ""),
  ];
  const signals = [{ id: "breath", op: "walk", label: "Random", in: [], range: SWING }];
  const routes = [{ source: "breath", path: "layers.top.sparkle.rate", depth: 1 }];
  const stack = { layers, signals, routes, front: ["layers.top.opacity", "layers.top.sparkle.rate"], dims: 2 as const };
  const names = (view: ReturnType<typeof panelOf<(typeof params)[number]>>) => [
    view.front.map((p) => p.name), view.loose.map((p) => p.name),
    view.sections.map((s) => [s.title, s.params.map((p) => p.name)]),
  ];
  // A front knob shows in its section too.
  expect(names(panelOf(params, stack, "top"))).toEqual([
    ["layers.top.opacity", "layers.top.sparkle.rate"], ["level"], [["Glints", ["layers.top.sparkle.rate"]]],
  ]);
  expect(panelOf(params, stack, "top").signals).toEqual([
    { title: "breath · random", name: "breath", kind: "random", reads: [], by: "on", at: Infinity, params: [params[4]], moves: ["layers.top.sparkle.rate"], feeds: [] },
  ]);
  expect(names(panelOf(params, stack, "base"))[1]).toEqual(["layers.base.wash.speed", "level"]);
  const lone = { ...stack, layers: layers.slice(0, 1), front: [] };
  expect(names(panelOf(params.slice(0, 2), lone, "base"))).toEqual([[], ["layers.base.wash.speed"], []]);
  // Off its defaults, a lone layer's mix shows, so it can be put back; with more layers it is in the rows.
  expect(names(panelOf(params.slice(0, 2), lone, "base", true))).toEqual([
    [], ["layers.base.wash.speed", "layers.base.opacity"], [],
  ]);
  expect(names(panelOf(params, stack, "top", true))).toEqual(names(panelOf(params, stack, "top")));
});

test("a knob says what it belongs to: its signal, or its layer when asked, and its node where another of its layer reads alike", () => {
  const rate = knob("", "breath");
  expect(isSignal(rate) && !isSignal(knob("base", "wash")) && !isMix(rate) && isMix(knob("base", ""))).toBe(true);
  const named = (label: string, layer: string, node: string) => ({ name: `${layer}.${node}.${label}`, label, layer, node, group: "" });
  const all = [named("Rate", "", "breath"), named("Speed", "base", "wash"), named("Opacity", "top", ""), named("Speed", "top", "a"), named("Speed", "top", "b")];
  const label = (p: (typeof all)[number]) => p.label;
  expect(all.map((p) => contextOf(p, all, label, true))).toEqual(["breath", "base", "top", "top · a", "top · b"]);
  expect(all.slice(0, 2).map((p) => contextOf(p, all, label, false))).toEqual(["breath", ""]);
  // A knob shown alone still names its node when another anywhere in its layer reads alike.
  expect(contextOf(all[3]!, all, label, false)).toBe("a");
});

test("a layer shows what it runs along its wiring, what it makes in a few words, and moves one place towards either end", () => {
  const program = {
    id: "fx",
    nodes: [
      { id: "waves", op: "osc", label: "Oscillator", in: [] },
      { id: "fold", op: "kaleid", label: "Kaleidoscope", in: ["waves"] },
      { id: "drift", op: "noise", label: "Noise", in: [] },
      { id: "warp", op: "modulate", label: "Ripple", in: ["fold", "drift"] },
      { id: "tint", op: "palette", label: "Palette", in: ["warp"] },
    ],
  };
  const echo = { id: "echo", nodes: [{ id: "below", op: "below", label: "Below", in: [] }, { id: "fb", op: "feedback", label: "Feedback", in: ["below"] }] };
  const below = { id: "x", nodes: [{ id: "below", op: "below", label: "Below", in: [] }] };
  expect([runs(layers[1]!), runs(program), runs(below)]).toEqual(["Sparkle", "Oscillator → Kaleidoscope → Ripple (+ Noise) → Palette", "Below"]);
  // The chain line shows only what the node sections do not: a node with no knobs, which has none.
  const all = new Set(program.nodes.map((n) => n.id));
  expect([chainSaysMore(program, all), chainSaysMore(program, new Set(["waves", "fold", "warp"])), chainSaysMore(echo, new Set(["fb"])), chainSaysMore(layers[1]!, new Set())]).toEqual([
    false, true, false, false,
  ]);
  // A palette that only colors what the layer starts from says nothing; two nodes of one op say which by id.
  const tinted = { id: "t", nodes: [{ id: "bars", op: "osc", label: "Oscillator", in: [] }, { id: "tint", op: "palette", label: "Palette", in: ["bars"] }] };
  const twins = { id: "n", nodes: [{ id: "a", op: "noise", label: "Noise", in: [] }, { id: "b", op: "noise", label: "Noise", in: ["a"] }] };
  expect([summaryOf(tinted), runs(twins)]).toEqual(["Oscillator", "Noise ‘a’ → Noise ‘b’"]);
  const comet = { id: "comet", nodes: [{ id: "comet", op: "pattern", label: "comet", in: [] }] };
  const ripple = { id: "ripple", nodes: [{ id: "ripple", op: "ripple", label: "Ripple", in: [] }] };
  expect([summaryOf(comet), summaryOf(ripple), summaryOf(layers[1]!), summaryOf(program), summaryOf(echo)]).toEqual([
    "", "", "Sparkle", "Oscillator\u00a0· Kaleidoscope", "Feedback on layers below", // a layer named as what it runs says nothing more; the dot stays with the source
  ]);
  expect([isPattern(layers[0]!), isPattern(program), isPattern(below)]).toEqual([true, false, false]);
  const three = [...layers, program];
  expect([moveTo(three, "top", true), moveTo(three, "top", false), moveTo(three, "fx", true), moveTo(three, "base", false)]).toEqual([
    2, 0, null, null,
  ]);
  expect(moveTo(three, "gone", true)).toBeNull();
  expect(mixAddress("top", "blend")).toBe("layers.top.blend");
});

test("the front knobs come first in front order, each once, and the rest keep theirs", () => {
  const named = ["a", "b", "c", "d"].map((name) => ({ name }));
  const { front, rest } = frontFirst(named, ["c", "gone", "a"]);
  expect([front.map((p) => p.name), rest.map((p) => p.name)]).toEqual([["c", "a"], ["b", "d"]]);
});

test("the routes into a knob include a part's, and say what modulates it, ± where the modulator swings both ways", () => {
  const routes = [
    { source: "breath", path: "layers.base.zoo.level", depth: 0.2 },
    { source: "macro", path: "layers.base.zoo.color.h", depth: 60 },
    { source: "macro", path: "layers.base.zoo.levels", depth: 1 },
    { source: "duck", path: "layers.base.zoo.level", depth: -0.3 },
  ];
  const signals: SignalItem[] = [
    { id: "breath", op: "lfo", label: "LFO", in: [], range: SWING },
    { id: "macro", op: "knob", label: "Macro", in: [], range: LEVEL },
    { id: "duck", op: "smooth", label: "Smooth", in: ["macro"], range: LEVEL }, // a smooth of a level is a level
  ];
  expect(routesInto(routes, "layers.base.zoo.level")).toEqual([routes[0], routes[3]]);
  expect(movedBy(routes, "layers.base.zoo.level", (_, d) => `${d} Hz`, signals)).toBe("modulated by ‘breath’ ±0.2 Hz; ‘duck’ −0.3 Hz");
  expect(movedBy(routes, "layers.base.zoo.color", (part, d) => `${d}${part === "h" ? "°" : ""}`, signals)).toBe("modulated by ‘macro’ on h +60°");
  expect(movedBy(routes, "layers.base.zoo.bands")).toBeNull();
  // A modulator the page does not know swings, as far as it can tell.
  expect(movedBy(routes.slice(0, 1), "layers.base.zoo.level")).toBe("modulated by ‘breath’ ±0.2");
  expect(routes.map((r) => depthSign(r, signals))).toEqual(["±", "+", "+", "−"]);
});

test("how far a route moves a knob reads as its control shows a value, the sign left to the line", () => {
  const opacity = { ...param("zoo", "level"), name: "layers.top.opacity", layer: "top", node: "" };
  expect(depthOf(opacity, "", 0.3)).toBe("30%");
  expect(depthOf(param("wave", "speed"), "", 0.1)).toBe("0.1 /s");
  const color = param("zoo", "color");
  expect([depthOf(color, "h", 60), depthOf(color, "s", 0.25)]).toEqual(["60°", "25%"]);
});

test("a main knob names its owner: its step where its layer has several, its layer where the look has several", () => {
  const program = { id: "base", nodes: [{ id: "fb", op: "feedback", label: "Feedback", in: [] }, { id: "tint", op: "palette", label: "Palette", in: ["fb"] }] };
  const two = [program, layers[1]!];
  expect(ownerOf(knob("base", "fb"), two)).toBe("fb · base");
  expect(ownerOf(knob("top", "sparkle"), two)).toBe("top"); // a pattern is its layer's one step
  expect(ownerOf(knob("top", ""), two)).toBe("top"); // a layer's own mix
  expect(ownerOf(knob("base", "fb"), [program])).toBe("fb"); // one layer: the step alone
  expect(ownerOf(knob("base", "wash"), layers.slice(0, 1))).toBe(""); // a lone pattern's knob
  expect(ownerOf(knob("", "breath"), two)).toBe("breath"); // a modulator's knob
});

test("a label reads in lower case on the page, but an acronym keeps its capitals", () => {
  expect(["LFO", "Envelope", "A", "Kaleidoscope"].map(pageCase)).toEqual(["LFO", "envelope", "a", "kaleidoscope"]);
});

test("each modulator the engine has reads by its RA-27 §12.2 name, the engine's label", () => {
  const signals = catalog.ops.filter((op) => op.sig === "signal");
  expect(signals.map(({ op, label }) => signalKind({ id: op, op, label, in: [] })).sort()).toEqual(
    ["LFO", "audio follower", "beat", "envelope", "macro", "random", "smooth"],
  );
});

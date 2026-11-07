// The running look's layer stack (pewpew.compose), as the aura state carries it.
import { percent, percentOf, withUnit } from "../params/format";
import type { Param } from "../params/schema";
// A knob's address is its param's `name`: `layers.<layer>.<node>.<arg>`,
// `layers.<layer>.opacity|blend|enabled` for a layer's own mix, or
// `signals.<signal>.<arg>` for a knob of one of the look's signals.

/** One node of a layer's program or a look's signals: its id, its op, what the page calls it (for
 * a `pattern` node, the pattern's name), and the ids of the nodes it reads (`in`). */
export interface NodeItem {
  readonly id: string;
  readonly op: string;
  readonly label: string;
  readonly in: readonly string[];
}

/** One of a look's signals (a modulator): a node, and the range of what it gives, -1..1 for one that
 * swings both ways, 0..1 for a level (pewpew.fx.ops.signal). */
export interface SignalItem extends NodeItem {
  readonly range: readonly [number, number];
}

/** One layer: its id and its program's nodes, in evaluation order. */
export interface LayerItem {
  readonly id: string;
  readonly nodes: readonly NodeItem[];
}

/** A signal driving the knob at `path` by up to `depth`, in that knob's units. */
export interface RouteItem {
  readonly source: string;
  readonly path: string;
  readonly depth: number;
}

export interface StackState {
  /** In render order: [0] is the bottom layer. */
  readonly layers: readonly LayerItem[];
  /** The look's signals, in the order they run. */
  readonly signals: readonly SignalItem[];
  /** The routes that run; a route whose knob a pick replaced rests and is left out. */
  readonly routes: readonly RouteItem[];
  /** The addresses of the knobs a page shows first. */
  readonly front: readonly string[];
  /** How many axes the map spans: 0 for a point, 1 a strip, 2 a panel or flat room, 3 a volume. */
  readonly dims: 0 | 1 | 2 | 3;
}

/** The layer id an address names (`layers.<layer>.…`), or null for another name. */
export function layerOf(address: string): string | null {
  const [head, layer] = address.split(".");
  return head === "layers" && layer ? layer : null;
}

/** A knob's place in the stack, as its describe record gives it. */
interface Placed {
  readonly layer: string;
  readonly node: string;
  readonly group: string;
}

/** Whether `p` is a layer's own mix knob (opacity, blend or enabled): it has a layer but no node. */
export function isMix(p: Placed): boolean {
  return p.layer !== "" && p.node === "";
}

/** Whether `p` is a layer's opacity, which reads as a percent, as the master does. */
export function isOpacity(p: Placed & { readonly name: string }): boolean {
  return isMix(p) && p.name === mixAddress(p.layer, "opacity");
}

/** Whether `p` is a knob of one of the look's signals: it has a node but no layer. */
export function isSignal(p: Placed): boolean {
  return p.layer === "" && p.node !== "";
}

/** `label` as the page shows a word: in lower case, except an acronym (`LFO`). */
export function pageCase(label: string): string {
  return /^[A-Z0-9]{2,}$/.test(label) ? label : label.toLowerCase();
}

/** What kind of modulator `node` is: its op's label from the engine (`LFO`, `audio follower`). */
export function signalKind(node: NodeItem): string {
  return pageCase(node.label);
}

/** A layer's nodes in the order a page lists them: along its wiring from what it starts from to
 * its output, each node after the nodes it reads (its first input's line, then the others), so
 * an extra input comes just before the node that reads it; nodes nothing reads last. */
export function nodeOrder(layer: LayerItem): readonly NodeItem[] {
  const byId = new Map(layer.nodes.map((n) => [n.id, n]));
  const seen = new Set<NodeItem>();
  const out: NodeItem[] = [];
  const visit = (n: NodeItem | undefined) => {
    if (!n || seen.has(n)) return;
    seen.add(n);
    for (const id of n.in) visit(byId.get(id));
    out.push(n);
  };
  visit(layer.nodes.at(-1));
  for (const n of layer.nodes) visit(n);
  return out;
}

/** How a section names node or signal `id` it reads: by its id, or, when a node and a signal share
 * it, its kind before it (`noise ‘drift’`). */
function refName(id: string, layers: readonly LayerItem[], signals: readonly NodeItem[], node: boolean): string {
  const nodes = layers.flatMap((l) => l.nodes);
  if (!nodes.some((n) => n.id === id) || !signals.some((n) => n.id === id)) return id;
  const it = node ? nodes.find((n) => n.id === id)! : signals.find((n) => n.id === id)!;
  return `${node ? it.label.toLowerCase() : signalKind(it)} ‘${id}’`;
}

/** A panel section's head: its name first, then the kind of what it is (a node's op, a signal's
 * kind; "" for a group), then what it reads when that is not plain: nothing for a node that reads
 * the node listed before it, or nothing; `by` the word before it: "←" for a node's inputs, "on" for
 * what a signal follows. `title` says it all in a line, and keys the section; `at` orders a layer's
 * node sections along its wiring (`nodeOrder`). */
export interface SectionHead {
  readonly title: string;
  readonly name: string;
  readonly kind: string;
  readonly reads: readonly string[];
  readonly by: "←" | "on";
  readonly at: number;
}

function head(name: string, kind: string, reads: readonly string[], at = Infinity, by: SectionHead["by"] = "←"): SectionHead {
  const title = `${name}${kind ? ` · ${kind}` : ""}${reads.length ? ` ${by} ${reads.join(", ")}` : ""}`;
  return { title, name, kind, reads, by, at };
}

/** The panel section a knob goes in, or null for none: a signal's knobs one each (`breath · LFO`,
 * and the signals it follows: `splash · envelope on kick`); in a layer of several nodes, each node's
 * (`fold · Kaleidoscope`; `warp · Modulate ← fold, drift`); else the knob's own group. */
export function sectionOf(p: Placed, layers: readonly LayerItem[], signals: readonly SignalItem[] = []): SectionHead | null {
  if (isSignal(p)) {
    const signal = signals.find((n) => n.id === p.node);
    const reads = (signal?.in ?? []).map((id) => refName(id, layers, signals, false));
    return head(p.node, signal ? signalKind(signal) : "signal", reads, Infinity, "on");
  }
  const layer = layers.find((l) => l.id === p.layer);
  const node = layer && layer.nodes.length > 1 ? layer.nodes.find((n) => n.id === p.node) : undefined;
  if (!layer || !node) return p.group ? head(p.group, "", []) : null;
  const order = nodeOrder(layer);
  const at = order.indexOf(node);
  const plain = !node.in.length || (node.in.length === 1 && node.in[0] === order[at - 1]?.id);
  const reads = plain ? [] : node.in.map((id) => refName(id, layers, signals, true));
  return node.id.toLowerCase() === node.label.toLowerCase() ? head(node.label, "", reads, at) : head(node.id, node.label, reads, at);
}

/** What knob `p` says it belongs to, among the look's knobs `all`: a signal's knob its signal; a
 * layer's knob its layer when `layered`, and its node too when another knob of that layer has the
 * same `caption`, by `node` (its id, unless given); "" when nothing needs saying. */
export function contextOf<P extends Placed & { readonly name: string }>(
  p: P,
  all: readonly P[],
  caption: (p: P) => string,
  layered: boolean,
  node: (p: P) => string = (q) => q.node,
): string {
  if (!p.layer) return p.node;
  const clash = !!p.node && all.some((q) => q.name !== p.name && q.layer === p.layer && q.node !== p.node && caption(q) === caption(p));
  return [layered ? p.layer : "", clash ? node(p) : ""].filter(Boolean).join(" · ");
}

/** Who owns main knob `p`, shown outside its step, among `layers` (RA-27b §3): its step, when its layer has
 * several, then its layer, when the look has several (`fb · base`); a signal's knob its signal; "" for a
 * knob of a lone pattern. */
export function ownerOf(p: Placed, layers: readonly LayerItem[]): string {
  if (!p.layer) return p.node;
  const layer = layers.find((l) => l.id === p.layer);
  const step = p.node && (layer?.nodes.length ?? 0) > 1 ? p.node : "";
  return [step, layers.length > 1 ? p.layer : ""].filter(Boolean).join(" · ");
}

export interface Section<P> extends SectionHead {
  readonly params: readonly P[];
  /** For a signal's section, the addresses of the knobs it moves. */
  readonly moves?: readonly string[];
  /** For a signal's section, the signals that read it. */
  readonly feeds?: readonly string[];
}

/** What the knob panel shows of a look's knobs `params` with layer `layer` picked. */
export interface PanelView<P> {
  /** The knobs the look lists in `front`, in its order. */
  readonly front: readonly P[];
  /** The look's signals' other knobs, a section each. */
  readonly signals: readonly Section<P>[];
  /** The picked layer's other knobs, in display order: those in no section, then each section. */
  readonly loose: readonly P[];
  readonly sections: readonly Section<P>[];
}

/** The knob panel of `stack` with layer `layer` picked: the look's front knobs, then its signals'
 * knobs and the picked layer's, each section by `sectionOf`; a front knob shows in its section
 * too, so a section always holds all its knobs. A lone layer's own mix shows only
 * while it is `mixed`, off its defaults: at them, over black, every blend shows the layer as it is
 * or black, and enabled and opacity repeat the blackout and the master. With more layers, each
 * layer's mix is in its row, and only the picked layer's other knobs show. A knob that names no
 * layer always shows. */
export function panelOf<P extends Placed & { readonly name: string }>(
  params: readonly P[],
  stack: StackState | null,
  layer: string | null,
  mixed = false,
): PanelView<P> {
  const layers = stack?.layers ?? [];
  const many = layers.length > 1;
  const { front } = frontFirst(params, stack?.front.length ? stack.front : stack ? pickedFront(stack, params) : []);
  const all = stack?.signals ?? [];
  const loose: P[] = [];
  const signals = new Map<string, { head: SectionHead; params: P[] }>();
  const sections = new Map<string, { head: SectionHead; params: P[] }>();
  for (const p of params) {
    if (isMix(p) ? many || !mixed : many && p.layer && p.layer !== layer) continue;
    const at = sectionOf(p, layers, all);
    const into = isSignal(p) ? signals : sections;
    if (!at) loose.push(p);
    else if (into.has(at.title)) into.get(at.title)!.params.push(p);
    else into.set(at.title, { head: at, params: [p] });
  }
  const routes = stack?.routes ?? [];
  const listed = (m: typeof sections) => [...m.values()].map(({ head, params }): Section<P> => ({ ...head, params }));
  const moved = (s: Section<P>): Section<P> => {
    const id = s.params[0]?.node ?? "";
    const moves = [...new Set(routes.filter((r) => r.source === id).map((r) => r.path))];
    return { ...s, moves, feeds: all.filter((n) => n.in.includes(id)).map((n) => n.id) };
  };
  const ordered = listed(sections).sort((a, b) => (a.at === b.at ? 0 : a.at < b.at ? -1 : 1));
  return { front, signals: listed(signals).map(moved), loose, sections: ordered };
}

/** How many knobs a look that lists none shows first (pewpew.fx.surprise FRONT). */
const FRONT = 3;

/** The knobs a look that lists none shows first, by the rule the engine picks a made look's by
 * (pewpew.fx.surprise `_front`): those the routes move, then each layer's first knob, the bottom
 * layer's first, at most FRONT. A layer's opacity is never one: its row shows it. None for a lone
 * pattern, whose knobs show under it. */
export function pickedFront(stack: StackState, params: readonly { readonly name: string }[]): string[] {
  const { layers, routes } = stack;
  const bottom = layers[0];
  if (!bottom || (layers.length === 1 && isPattern(bottom))) return [];
  const firsts = layers.flatMap((l) => {
    const node = l.nodes[0];
    const first = node && params.find((p) => p.name.startsWith(`layers.${l.id}.${node.id}.`));
    return first ? [first.name] : [];
  });
  return [...new Set([...routes.map((r) => r.path), ...firsts])].slice(0, FRONT);
}

/** `params` split into the knobs `front` names, in its order, and the rest, in theirs. */
export function frontFirst<P extends { readonly name: string }>(
  params: readonly P[],
  front: readonly string[],
): { readonly front: P[]; readonly rest: P[] } {
  const named = new Set(front);
  return {
    front: front.flatMap((name) => params.filter((p) => p.name === name)),
    rest: params.filter((p) => !named.has(p.name)),
  };
}

/** The routes that move the knob at address `name`, or one of its parts (`name.h`). */
export function routesInto(routes: readonly RouteItem[], name: string): RouteItem[] {
  return routes.filter((r) => r.path === name || r.path.startsWith(`${name}.`));
}

/** How far route `r` moves its knob, by sign (RA-27 §12.3): ± for a signal that swings both ways (an
 * LFO, a random, a smooth of either), else the route's own sign, + or −, as a level moves a knob one way
 * only. A signal not in `signals` swings, as far as the page knows. */
export function depthSign(r: RouteItem, signals: readonly SignalItem[]): "±" | "+" | "−" {
  const range = signals.find((n) => n.id === r.source)?.range;
  return !range || range[0] < 0 ? "±" : r.depth < 0 ? "−" : "+";
}

/** What modulates the knob at address `name`, in words, each modulator by its name (`modulated by
 * ‘breath’ ±0.2 Hz`), or null when no route does; `depth` writes how far a route moves the knob, or a part
 * of it, as its control shows a value (`30%`), and `depthSign` the sign before it. A route into a part
 * names it (`modulated by ‘tint’ on h +60°`); several join with "; ". */
export function movedBy(
  routes: readonly RouteItem[],
  name: string,
  depth: (part: string, depth: number) => string = (_, d) => String(d),
  signals: readonly SignalItem[] = [],
): string | null {
  const into = routesInto(routes, name);
  if (!into.length) return null;
  const each = into.map((r) => {
    const part = r.path === name ? "" : r.path.slice(name.length + 1);
    return `‘${r.source}’${part ? ` on ${part}` : ""} ${depthSign(r, signals)}${depth(part, Math.abs(r.depth))}`;
  });
  return `modulated by ${each.join("; ")}`;
}

/** How far a route moves `p`, or its part `part`, by `depth` (at least 0), as `p`'s control shows a value: a
 * percent for a layer's opacity and a color's 0..1 part (`30%`), else in its unit (`0.2 Hz`). */
export function depthOf(p: Param, part: string, depth: number): string {
  const spec = p.kind === "color" ? (part in p.parts ? p.parts[part as keyof typeof p.parts] : null) : p.kind === "float" || p.kind === "int" ? p : null;
  return isOpacity(p) || (p.kind === "color" && spec && percentOf(spec)) ? percent(depth) : withUnit(String(depth), spec?.unit ?? "");
}

/** The node at `address` (`layers.<layer>.<node>`) among `layers`, or null. */
export function nodeAt(address: string, layers: readonly LayerItem[]): NodeItem | null {
  const layer = layers.find((l) => l.id === layerOf(address));
  return layer?.nodes.find((n) => `layers.${layer.id}.${n.id}` === address) ?? null;
}

/** Whether layer `layer` runs one gallery pattern, which a pick replaces as it is. */
export function isPattern(layer: LayerItem): boolean {
  const [only, ...more] = layer.nodes;
  return !!only && !more.length && only.op === "pattern";
}

/** Whether layer `layer` reads the layers under it (a `below` node): an effect on them. */
export function readsBelow(layer: LayerItem): boolean {
  return layer.nodes.some((n) => n.op === "below");
}

/** Layer `layer`'s nodes along its wiring, from what it starts from to its output, by each one's first input. */
function chainOf(layer: LayerItem): NodeItem[] {
  const byId = new Map(layer.nodes.map((n) => [n.id, n]));
  const chain: NodeItem[] = [];
  for (let n = layer.nodes.at(-1); n && !chain.includes(n); n = byId.get(n.in[0] ?? "")) chain.unshift(n);
  return chain;
}

/** What layer `layer` makes, in a few words: its pattern; for an effect on the layers under it,
 * what it does to them (`feedback on layers below`); else what it starts from and its first step
 * after that, a palette that only colors it left out (`Oscillator · Kaleidoscope`). "" when that
 * would only say its id again (a source added as `ripple`). */
export function summaryOf(layer: LayerItem): string {
  const text = summaryText(layer);
  return text.toLowerCase() === layer.id.toLowerCase() ? "" : text;
}

function summaryText(layer: LayerItem): string {
  const [first] = layer.nodes, last = layer.nodes.at(-1);
  if (!first || !last) return "";
  if (isPattern(layer)) return first.label;
  if (readsBelow(layer)) {
    const what = layer.nodes.filter((n) => n.op !== "below").map((n) => n.label).join(" · ");
    return what ? `${what} on layers below` : "the layers below";
  }
  const [source = first, step] = chainOf(layer).filter((n) => !(n === last && n.op === "palette" && n !== first));
  return step ? `${source.label}\u00a0· ${step.label}` : source.label;
}

/** What node `n` of `layer` is called in a line a person reads: its op's label, and its id after it
 * where another node of the layer runs the same op (`noise ‘drift’`). */
function opName(n: NodeItem, layer: LayerItem): string {
  const twin = layer.nodes.some((m) => m !== n && m.label === n.label);
  return twin ? `${n.label} ‘${n.id}’` : n.label;
}

/** What layer `layer` runs, in full: its pattern, or its program along its wiring, from what it
 * starts from to its output, each node by what it does (`opName`), each node a node reads besides
 * the one before it after it (`Oscillator → Kaleidoscope → Modulate (+ Noise) → Palette`). */
export function runs(layer: LayerItem): string {
  if (isPattern(layer)) return layer.nodes[0]!.label;
  const byId = new Map(layer.nodes.map((n) => [n.id, n]));
  const name = (id: string) => (byId.has(id) ? opName(byId.get(id)!, layer) : id);
  return chainOf(layer).map((n) => {
    const more = n.in.slice(1);
    return more.length ? `${opName(n, layer)} (+ ${more.map(name).join(", ")})` : opName(n, layer);
  }).join(" → ");
}

/** Whether the line `runs` writes for `layer` says more than its row (`summaryOf`) and its open row's
 * node sections, which name each node with knobs (those in `knobbed`) in order, with what it reads: a
 * program of more than two nodes, one of which has no knobs, and so no section. */
export function chainSaysMore(layer: LayerItem, knobbed: ReadonlySet<string>): boolean {
  return !isPattern(layer) && layer.nodes.length > 2 && layer.nodes.some((n) => !knobbed.has(n.id));
}

/** The render index a `move_layer` sends to move layer `id` one place `up` (towards the top) or
 * down, or null at that end. */
export function moveTo(layers: readonly LayerItem[], id: string, up: boolean): number | null {
  const i = layers.findIndex((l) => l.id === id);
  const to = up ? i + 1 : i - 1;
  return i < 0 || to < 0 || to >= layers.length ? null : to;
}

/** The address of mix knob `knob` of layer `id`. */
export function mixAddress(id: string, knob: "opacity" | "blend" | "enabled"): string {
  return `layers.${id}.${knob}`;
}
